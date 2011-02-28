"""Simple wrapper for standard checkout as implemented in satchmo.payment.views"""

from livesettings import config_get_group
from payment.views import confirm, payship
    
globalgateway = config_get_group('PAYMENT_GLOBALGATEWAY')
    
def pay_ship_info(request):
    return payship.credit_pay_ship_info(request, globalgateway)
    
def confirm_info(request):
    return confirm.credit_confirm_info(request, globalgateway)


