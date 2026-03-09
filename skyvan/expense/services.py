from .models import  Expense, ExpenseType


def get_expenses_list():
    return Expense.objects.filter(deleted=False)

def get_expense_type_list():
    return ExpenseType.objects.filter(deleted=False)

