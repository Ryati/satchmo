from django.utils.translation import ugettext_lazy as _
from livesettings import *

# this is so that the translation utility will pick up the string
gettext = lambda s: s


PAYMENT_GROUP = ConfigurationGroup('PAYMENT_GLOBALGATEWAY', 
                                   _('Globalgateway Payment Module Settings'), 
                                   ordering = 109)

config_register_list(
    BooleanValue(PAYMENT_GROUP, 
                 'LIVE', 
                 description=_("Accept real payments"),
                 help_text=_("False if you want to be in test mode"),
                 default=False),

    ModuleValue(PAYMENT_GROUP,
                'MODULE',
                description=_('Implementation module'),
                hidden=True,
                default = 'payment.modules.globalgateway'),

    StringValue(PAYMENT_GROUP,
                'KEY',
                description=_("Module key"),
                hidden=True,
                default = 'GLOBALGATEWAY'),

    StringValue(PAYMENT_GROUP,
                'LABEL',
                description=_('English name for this group on the checkout screens'),
                default = 'Credit Card Payment',
                help_text = _('This will be passed to the translation utility')),

    StringValue(PAYMENT_GROUP,
                'URL_BASE',
                description=_('The url base used for constructing urlpatterns which will use this module'),
                default = '^credit/'),

    MultipleStringValue(PAYMENT_GROUP,
                        'CREDITCHOICES',
                        description=_('Available credit cards'),
                        choices = (
                            (('Visa','Visa')),
                            (('Mastercard','Mastercard')),
                            (('Discover','Discover')),
                            (('American Express', 'American Express'))),
                        default = ('Visa', 'Mastercard', 'Discover')),

    StringValue(PAYMENT_GROUP, 
                'CONNECTION',
                description=_("Address for live payment transactions"),
                help_text=_("""This is the address to submit live transactions."""),
                default='secure.linkpt.net'),

    StringValue(PAYMENT_GROUP, 
                'CONNECTION_TEST',
                description=_("Adress for test payment transactions"),
                help_text=("""This is the address to submit test transactions"""),
                default='staging.linkpt.net'),

    IntegerValue(PAYMENT_GROUP, 
                'PORT',
                description=_("Port for live payment transactions"),
                help_text=("""This is the port to submit live transactions"""),
                default='1129'),

    IntegerValue(PAYMENT_GROUP, 
                 'PORT_TEST',
                 description=_("Port for test payment transactions"),
                 help_text=("""This is the port to submit test transactions"""),
                 default='1129'),

    StringValue(PAYMENT_GROUP, 
                'SSL_KEY',
                description=_("Live payment key file location."),
                help_text=("""Path and file name of the key file for live transactions"""),
                default='/path/to/pem/0123456789.pem'),

    StringValue(PAYMENT_GROUP, 
                'SSL_KEY_TEST',
                description=_("Test payment key file location."),
                help_text=("""Path and file name of the key file for test transactions"""),
                default='/path/to/pem/0123456789.pem'),

    BooleanValue(PAYMENT_GROUP, 
                 'AVS', 
                 description=_("Use Address Verification System (AVS)?"), 
                 default=True),

    BooleanValue(PAYMENT_GROUP,
                 'STRICT_AVS',
                 description=_("Use strict address verification.  Less likely to have fraud but may keep some people for being able to purchase."),
                 defalt=True),

    StringValue(PAYMENT_GROUP, 
                'MERCHANT_ID', 
                description=_('Your First Data/Global Gateway merchant ID'),
                default="0123456789"),
    
    BooleanValue(PAYMENT_GROUP,
                 'EXTRA_LOGGING',
                 description=_("Verbose logs"),
                 help_text=_("Add extensive logs during post."),
                 default=False)
)

