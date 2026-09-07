import django_tables2 as tables

from customer.models import CustomerHSE, CustomerPalletLocationAvailability, CustomerInventory, CustomerDamage, \
    CustomerExpiry, CustomerReturns, CustomerWHOutbound, CustomerTransportationOutbound, CustomerInbound


class NumberedTable(tables.Table):
    counter = tables.TemplateColumn('{{ row_counter|add:1 }}', orderable=False, verbose_name='#')

    class Meta:
        attrs = {'class': 'table'}


class InboundTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerInbound


class OutboundTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerTransportationOutbound


class CustomerWHOutboundTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerWHOutbound


class ReturnsTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerReturns


class ExpiryTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerExpiry


class DamageTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerDamage


class InventoryTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerInventory


class PalletLocationAvailabilityTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerPalletLocationAvailability


class HseTable(NumberedTable):
    class Meta(NumberedTable.Meta):
        model = CustomerHSE

