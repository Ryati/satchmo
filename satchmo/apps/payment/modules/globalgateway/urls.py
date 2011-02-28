from django.conf.urls.defaults import *
from livesettings import config_value, config_get_group
from satchmo_store.shop.satchmo_settings import get_satchmo_setting

config = config_get_group('PAYMENT_GLOBALGATEWAY')

ssl = get_satchmo_setting('SSL', default_value=False)

urlpatterns = patterns('payment',
     (r'^$', 'modules.globalgateway.views.pay_ship_info', {'SSL':ssl}, 'GLOBALGATEWAY_satchmo_checkout-step2'),
     (r'^confirm/$', 'modules.globalgateway.views.confirm_info', {'SSL':ssl}, 'GLOBALGATEWAY_satchmo_checkout-step3'),
     (r'^success/$', 'views.checkout.success', {'SSL':ssl}, 'GLOBALGATEWAY_satchmo_checkout-success'),
)
