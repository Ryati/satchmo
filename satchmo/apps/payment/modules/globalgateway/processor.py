#import urllib2
import logging, re

from payment.modules.base import BasePaymentProcessor, ProcessorResult

log = logging.getLogger("payment.modules.globalgateway.processor")

TIME = re.compile(r"<r[ _]time>(?P<value>.*)</r[ _]time>")
CSP = re.compile(r"<r[ _]csp>(?P<value>.*)</r[ _]csp>")
REF = re.compile(r"<r[ _]ref>(?P<value>.*)</r[ _]ref>")
ERROR = re.compile(r"<r[ _]error>(?P<value>.*)</r[ _]error>")
ORDERNUM = re.compile(r"<r[ _]ordernum>(?P<value>.*)</r[ _]ordernum>")
MESSAGE = re.compile(r"<r[ _]message>(?P<value>.*)</r[ _]message>")
CODE = re.compile(r"<r[ _]code>(?P<value>.*)</r[ _]code>")
TDATE = re.compile(r"<r[ _]tdate>(?P<value>.*)</r[ _]tdate>")
AUTHRESPONSE = re.compile(r"<r[ _]authresponse>(?P<value>.*)</r[ _]authresponse>")
APPROVED = re.compile(r"<r[ _]approved>(?P<value>.*)</r[ _]approved>")
AVS = re.compile(r"<r[ _]avs>(?P<value>.*)</r[ _]avs>")

ADDRNUM = re.compile(r"^(?P<value>\d+)")


GOOD_AVS = ["YYY", "YYA", "YYD", "YYF", "YYM", "NYP", "NNI", "NNC", "XXE", ]
BAD_AVS = ["NNN", "NNC", "NNI", ]
EITHER_AVS = ["NYZ", "YNA", "XXU", "XXS", "XXE", "XXG", "YNB", "NYP", ]

GOOD_CVM = ["M",]
BAD_CVM = ["N",]
EITHER_CVM = ["P","S","U","X"]

class PaymentProcessor(BasePaymentProcessor):
    """
    First Data Global Gateway payment processing module
    You must have an account with First Data Global Gateway in order to use this module
    
    """
    def __init__(self, settings):
        super(PaymentProcessor, self).__init__('GLOBALGATEWAY', settings)
        self.settings = settings
        self.contents = ''
        if settings.LIVE.value:
            self.testflag = 'FALSE'
            self.connection = settings.CONNECTION.value
            self.path = 'lpc/servlet/lppay'
            self.port = settings.PORT.value
            self.sslkey = settings.SSL_KEY.value

        else:
            self.testflag = 'TRUE'
            self.connection = settings.CONNECTION_TEST.value
            self.path = 'lpc/servlet/lppay'
            self.port = settings.PORT_TEST.value
            self.sslkey = settings.SSL_KEY_TEST.value
            
        self.configuration = {
            'merchantID' : settings.MERCHANT_ID.value
            }

    def prepare_data(self, order):
        from satchmo_utils.numbers import trunc_decimal
        #import pdb
        #pdb.set_trace()
        self.order = order
        addrnum = ADDRNUM.search(order.bill_street1)
        if addrnum is not None:
            addrnum = addrnum.group("value")
        self.bill_to = {
            'firstName' : order.contact.first_name,
            'lastName' : order.contact.last_name,
            'street1': order.bill_street1,
            'street2': order.bill_street2,
            'addrnum': addrnum,
            'city': order.bill_city,
            'state' : order.bill_state,
            'postalCode' : order.bill_postal_code,
            'country': order.bill_country,
            'email' : order.contact.email,
            'phoneNumber' : order.contact.primary_phone,
            # Can add additional info here if you want to but it's not required
            }
        exp = order.credit_card.expirationDate.split('/')
        self.card = {
            'accountNumber' : order.credit_card.decryptedCC,
            'expirationMonth' : exp[0],
            'expirationYear' : exp[1],
            'cvNumber' : order.credit_card.ccv
            }
        #currency = self.settings.CURRENCY_CODE.value
        currency = 'USD'
        currency = currency.replace("_", "")
        self.purchase_totals = {
            'currency' : currency,
            'grandTotalAmount' : "%.02f"%trunc_decimal(order.balance, 2),
            'shipping' : "%.02f"%trunc_decimal(order.shipping_sub_total,2),
            'tax' : "%.02f"%trunc_decimal(order.tax+order.shipping_tax,2),
            'sub_total': "%.02f"%trunc_decimal(order.discounted_sub_total,2),
        }


    def process_error(self, error):
        pieces = error.split(":",1)
        return {"message": pieces[1].strip(),
                "code": pieces[0].lstrip("SG-0"),
                "full_code": pieces[0]}


    def capture_payment(self, testing=False, order=None, amount=None):
        """
        Creates and sends XML representation of transaction to First Data Global Gateway
        
        """
        from django.template import Context, loader
        import httplib
        
        #import pdb
        #pdb.set_trace()

        c = Context({
            'config' : self.configuration,
            'merchantReferenceCode' : self.order.id,
            'billTo' : self.bill_to,
            'purchaseTotals' : self.purchase_totals,
            'card' : self.card,
            'order': self.order,
        })

        request = loader.render_to_string('shop/checkout/globalgateway/request.xml',{},c)

        log.debug("Request:\n%s"%request)
        
        #payment = self.record_payment(order = self.order, amount = amount, transaction_id="GlobalGateway:Fake",reason_code="Fake")

        #return ProcessorResult(self.key, True, "Not a real transaction.", payment=payment)

        connection = httplib.HTTPSConnection(self.connection, self.port, key_file=self.sslkey, cert_file=self.sslkey)
        connection.request('POST', self.path, body=request)
        try:
            f = connection.getresponse()
        except httplib.HTTPSError, e:
            # I'm not sure what I'm doing with this try/except
            # ...
            return(False, '999', 'Problem parsing results')

        all_results = f.read()
        connection.close()

        self.log_extra("Global Gateway Response: %s"%all_results)

        error = ERROR.search(all_results)
        approved = APPROVED.search(all_results)
        ref = REF.search(all_results)
        ordernum = ORDERNUM.search(all_results)
        message = MESSAGE.search(all_results)
        code = CODE.search(all_results)
        avs = AVS.search(all_results)

        response_message = message.group('value')
        payment = None
        success = False

        transaction_id = "Unable to get transaction id."
        if ref is not None:
            transaction_id = ref.group("value")
        elif ordernum is not None and transaction_id == "":
            transaction_id = "ORDERNUM: %s"%ordernum.group("value")

        if approved is not None and approved.group('value').lower() == "approved":
            success = True
        elif self.settings.AVS.value:
            if avs is not None:
                avs_value = avs.group("value")[:3]
                cvm = avs.group("value")[-1:]

                if avs_value in BAD_AVS:
                    response_message = "There is a problem with your billing address."
                elif avs_value in EITHER_AVS and self.settings.STRICT_AVS == True:                   
                    response_message = "There is a problem with your billing address."
                if cvm in BAD_CVM:
                    response_message = "There is a problem with your credit card information.  Please check the number, expiration date, and verification code."
                elif cvm in EITHER_CVM and self.settings.STRICT_AVS == True:
                    response_message = "There is a problem with your credit card information.  Please check the number, expiration date, and verification code."
        if success:
            reason_code = ""
            if code is not None:
                reason_code = code.group("value")

            if not testing:
                payment = self.record_payment(order = self.order, amount = amount, transaction_id = transaction_id, reason_code = reason_code)
        else:
            reason_code = ""
            if error is not None:
                reason_code = error.group("value")
                if response_message == "DECLINED":
                    error_dict = self.process_error(reason_code)
                    if error_dict['code'][:2] == "23":
                        response_message = error_dict['message']

            if not testing:
                payment = self.record_failure(amount = amount, transaction_id = transaction_id, reason_code = reason_code, details = response_message)
             
        if not testing:
            return ProcessorResult(self.key, success, response_message, payment=payment)
        else:
            return (self.key,success,
                    response_message,
                    {"request":request,
                     "response":all_results},
                    {"error":error.group("value"),
                     "approved":approved.group("value"),
                     "ref":ref.group("value"),
                     "ordernum":ordernum.group("value"),
                     "message":message.group("value"),
                     "code":code.group("value"),
                     "avs":avs.group("value"),
                    })


# When a payment is submitted in test mode ending in these dollar amounts, the following errors are returned

# NATHAN: I'm not sure about this section, the docs don't mention it
#        r_error text                                                 r_approved text

# $xx.00                                                              APPROVED
# $xx.01 SGS-002100: The server encountered a network error           TRY AGAIN
# $xx.02 SGS-002000: The server encountered an error                  FAILURE
# $xx.03 SGS-002000: The server encountered an error                  DUPLICATE
# $xx.04 SGS-002000: The server encountered an error                  INVALID MERCHANT
# $xx.05 SGS-002300: There was an invalid transaction reported        INVALID TRANSACTION
# $xx.08 SGS-002300: The transaction has an invalid card number,      MICR INVALID CARD
#                    number or routing number
# $xx.10 SGS-000002: R:Referral (call voice center)                   CALL AUTH CENTER
# $xx.56 SGS-000001: D:Declined:NNN                                   DECLINED
# $xx.58 SGS-002300: The transaction has an invalid card number,      MICR INVALID CARD
#                    number or routing number
# $xx.59 SGS-002300: No credit card expiration year provided          EXPIRED CARD
# $xx.60 SGS-000002: R:Referral (call voice center)                   CALL AUTH CENTER
# $xx.99 SGS-002300: This transaction was previously approved         DUPLICATE APPROVED

#NATHAN: From the PDF documentation for testing
# To control authorization result
#Penny Amount | Result   | Error Code
# xx.00       | Approved |
# xx.10       | Declined | 1
# xx.11       | Declined | 1
# xx.20       | Declined | 10501
# xx.21       | Declined | 10502
# xx.22       | Declined | 10503
# xx.23       | Declined | 2
# xx.24       | Declined | 2300
# xx.25       | Declined | 2300
# xx.26       | Declined | 2300
# xx.27       | Declined | 2301
# xx.28       | Declined | 2304
# xx.29       | Declined | 5002
# xx.30       | Declined | 5003
# xx.31       | Declined | 5005
# xx.35       | Approved |
# xx.40       | Approved |
# xx.51       | Approved |
# xx.63       | Approved |
# xx.71       | Approved |
# xx.83       | Approved |

# To control AVS response, pass the Zip Code digits specified below:
# xx00x     YNA
# xx01x     YNB
# xx02x     NNC
# xx03x     YYD
# xx04x     XXE
# xx05x     YYF
# xx06x     XXG
# xx07x     NNI
# xx08x     YYM
# xx09x     NNN
# xx10x     NYP
# xx11x     XXR
# xx12x     XXS
# xx13x     XXU
# xx14x     NYW
# xx15x     YYX
# xx16x     YYY
# xx17x     NYZ

# AVS Error Codes [Visa, MaasterCard, Discover, American Express]
# YY[Y,Y,A,Y] Address and zip code match
# NY[Z,Z,Z,Z] Only Zip code matches
# YN[A,A,A,A] Only address matches
# NN[N,N,N,N] Niether the address nor the zip code match
# XX[-,W,-,-] Card number not on File
# XX[U,U,U,U] Address information not verified for domestic transaction
# XX[R,-,R,R] Retry - system unavailable
# XX[S,-,S,S] Service not supported
# XX[E,-,-,-] AVS not allowed for card type
# XX[-,-,-,-] Address verification has been requested but not received
# XX[G,-,-,-] Global non-AVS participant
# YN[B,-,-,-] Street address matches for international transaction; postal code not verified.
# NN[C,-,-,-] Street address and Postal code not verified for international transaction
# YY[D,-,-,-] Street address and postal code match for international transaction
# YY[F,-,-,-] Street address and Postal code match for international transaction. (UK only)
# NN[I,-,-,-] Address information not verified for international transaction
# YY[M,-,-,-] Street address and Postal code match for international transaction
# NY[P,-,-,-] Postal codes match for international transaction, street address not verified.

# To control the CVM respons pass the zip cod digit specified:
# xxxx0    M
# xxxx1    N
# xxxx2    P
# xxxx3    S
# xxxx4    U
# xxxx5    X
# xxxx6    Y

# Card Code Definitions
# M Card code matches
# N Card code does not match
# P Not processed
# S Merchant has indicated that the card code is not present on the card
# U Issuer is not certified and/or has not provided encryption keys
# X No response from the credit card association was received

def test(amount="27.00",zip_code="85030"):
    """
    This is for testing - enabling you to run from the command line and make
    sure everything is ok
    """
    import os, time
    from livesettings import config_get_group

    # Set up some dummy classes to mimic classes being passed through Satchmo
    class testContact(object):
        pass
    class testCC(object):
        pass
    class testOrder(object):
        def __init__(self):
            self.contact = testContact()
            self.credit_card = testCC()
        def order_success(self):
            pass

    sampleOrder = testOrder()
    sampleOrder.contact.first_name = 'Chris'
    sampleOrder.contact.last_name = 'Smith'
    sampleOrder.contact.primary_phone = '801-555-9242'
    sampleOrder.contact.email = 'test@testing.com'
    sampleOrder.bill_street1 = '123 Main Street'
    sampleOrder.bill_street2 = ''
    sampleOrder.bill_postal_code = zip_code
    sampleOrder.bill_state = 'TN'
    sampleOrder.bill_city = 'Some City'
    sampleOrder.bill_country = 'US'
    sampleOrder.total = amount
    sampleOrder.balance = amount
    sampleOrder.id = int(time.time())
    sampleOrder.credit_card.decryptedCC = '6011000000000012'
    sampleOrder.credit_card.expirationDate = "10/2011"
    sampleOrder.credit_card.ccv = "144"

    payment_settings = config_get_group('PAYMENT_GLOBALGATEWAY')
    if payment_settings.LIVE.value:
        print "Warning.  You are submitting a live order.  Global Gateway system is set LIVE."

    processor = PaymentProcessor(payment_settings)
    processor.prepare_data(sampleOrder)
    results = processor.process(testing=True)
    print results
    return results


