from django.db import models


class Ticket(models.Model):
	ticket_id = models.BigAutoField(primary_key=True)
	ticket_code = models.CharField(max_length=50, unique=True)
	order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='tickets')
	ticket_category = models.ForeignKey('events.TicketCategory', on_delete=models.CASCADE)
	seat = models.ForeignKey('accounts.Seat', on_delete=models.SET_NULL, null=True, blank=True)
	purchase_date = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = 'ticket'

	def __str__(self):
		return self.ticket_code
