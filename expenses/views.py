import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from expenses import utils

from .forms import BudgetForm, ExpenseForm
from .models import Budget, Expense

import matplotlib.pyplot as plt
import io
import base64


@login_required
def homepage(request):
    Expense.objects.add_testuser_expenses(request)

    # Получаем все расходы текущего пользователя, отсортированные по дате
    user_expenses = Expense.objects.filter(owner=request.user).order_by("date")

    # Создаём словарь для хранения сумм расходов по дням
    line_chart_data = {}
    for expense in user_expenses:
        date = expense.date.strftime("%Y-%m-%d")
        line_chart_data[date] = line_chart_data.get(date, 0) + float(expense.amount)

    # Сортируем данные по дате
    sorted_dates = list(line_chart_data.keys())
    sorted_amounts = list(line_chart_data.values())

    # Генерация графика с Matplotlib
    plt.figure(figsize=(10, 7))
    plt.plot(sorted_dates, sorted_amounts, marker="o", linestyle="-", color="orange")
    plt.title("Общие расходы по дням")
    plt.xlabel("Дата")
    plt.ylabel("Сумма (€)")
    plt.xticks(rotation=45)
    plt.grid(True)

    # Сохраняем график в буфер памяти
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    # Кодируем изображение в base64
    graph = base64.b64encode(image_png).decode("utf-8")
    plt.close()

    context = {
        "expenses": user_expenses,
        "graph": graph,
    }

    return render(request, "homepage.html", context)


@login_required
def charts(request):
    expenses = Expense.objects.filter(owner=request.user).order_by("date")
    budget = Expense.objects.get_budget(request.user)
    statistics = Expense.objects.get_statistics(request.user)

    # Функция для создания линейного графика
    def generate_line_chart():
        dates = [expense.date for expense in expenses]
        amounts = [expense.amount for expense in expenses]

        plt.figure(figsize=(10, 5))
        plt.plot(dates, amounts, marker='o')
        plt.title("Общие расходы по дням")
        plt.xlabel("Дата")
        plt.ylabel("Сумма (€)")
        plt.xticks(rotation=45)
        plt.grid(True)

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        buffer.close()
        plt.close()
        return image

    # Функция для создания столбчатого графика по месяцам
    def generate_monthly_expenses_chart():
        from collections import defaultdict
        import calendar

        monthly_data = defaultdict(float)
        for expense in expenses:
            month = expense.date.strftime("%Y-%m")
            monthly_data[month] += float(expense.amount)

        months = sorted(monthly_data.keys())
        amounts = [monthly_data[month] for month in months]

        plt.figure(figsize=(10, 5))
        plt.bar(months, amounts, color='skyblue')
        plt.title("Расходы по месяцам")
        plt.xlabel("Месяц")
        plt.ylabel("Сумма (€)")
        plt.xticks(rotation=45)
        plt.grid(True)

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        buffer.close()
        plt.close()
        return image

    # Функция для создания столбчатого графика по неделям
    def generate_weekly_expenses_chart():
        from collections import defaultdict

        weekly_data = defaultdict(float)
        for expense in expenses:
            week = expense.date.strftime("%Y-%U")
            weekly_data[week] += float(expense.amount)

        weeks = sorted(weekly_data.keys())
        amounts = [weekly_data[week] for week in weeks]

        plt.figure(figsize=(10, 5))
        plt.bar(weeks, amounts, color='lightcoral')
        plt.title("Расходы по неделям")
        plt.xlabel("Неделя")
        plt.ylabel("Сумма (€)")
        plt.xticks(rotation=45)
        plt.grid(True)

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        buffer.close()
        plt.close()
        return image

    # Функция для создания круговой диаграммы по категориям
    def generate_pie_chart():
        from collections import defaultdict

        category_data = defaultdict(float)
        for expense in expenses:
            category_data[expense.category] += float(expense.amount)

        categories = list(category_data.keys())
        amounts = list(category_data.values())

        plt.figure(figsize=(8, 8))
        plt.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=140)
        plt.title("Расходы по категориям")

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        buffer.close()
        plt.close()
        return image

    # Генерация всех графиков
    chart_images = {
        "line_chart": generate_line_chart(),
        "monthly_chart": generate_monthly_expenses_chart(),
        "weekly_chart": generate_weekly_expenses_chart(),
        "pie_chart": generate_pie_chart(),
    }

    context = {
        "expenses": expenses,
        "budget": budget,
        "statistics": statistics,
        "chart_images": chart_images,
    }

    return render(request, "charts.html", context)


@login_required
def create_expense(request):
    template = "create_expense.html"

    if request.method != "POST":
        # No data submitted; create a blank form.
        form = ExpenseForm()
    else:
        # POST data submitted; process data.
        form = ExpenseForm(request.POST)
        if form.is_valid():
            new_expense = form.save(commit=False)
            new_expense.owner = request.user
            new_expense.save()
            return redirect("expenses:home")

    context = locals()
    return render(request, template, context)


@login_required
def view_expense(request, pk):
    template = "view_expense.html"
    expense = get_object_or_404(Expense, pk=pk)
    context = locals()

    return render(request, template, context)


@login_required
def update_expense(request, pk):
    template = "update_expense.html"
    expense = get_object_or_404(Expense, pk=pk)

    if request.method != "POST":
        form = ExpenseForm(instance=expense)

    else:
        form = ExpenseForm(instance=expense, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect("expenses:home")

    context = locals()
    return render(request, template, context)


@login_required
def delete_expense(request, pk):
    template = "delete_expense.html"
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == "POST":
        expense.delete()
        return redirect("expenses:home")

    return render(request, template, {})


@login_required
def create_budget(request):
    template = "create_budget.html"

    if request.method != "POST":
        # No data submitted; create a blank form.
        form = BudgetForm()
    else:
        # POST data submitted; process data.
        form = BudgetForm(request.POST)
        if form.is_valid():
            new_budget = form.save(commit=False)
            new_budget.owner = request.user
            new_budget.save()
            return redirect("expenses:home")

    context = locals()
    return render(request, template, context)


@login_required
def update_budget(request):
    template = "update_budget.html"
    budget = get_object_or_404(Budget, owner=request.user)

    if request.method != "POST":
        form = BudgetForm(instance=budget)

    else:
        form = BudgetForm(instance=budget, data=request.POST)
        if form.is_valid():
            updated_budget = form.save(commit=False)
            updated_budget.owner = request.user
            updated_budget.save()
            return redirect("expenses:home")

    context = locals()
    return render(request, template, context)


@login_required
def delete_budget(request):
    template = "delete_budget.html"
    budget = get_object_or_404(Budget, owner=request.user)

    if request.method == "POST":
        budget.delete()
        return redirect("expenses:home")

    return render(request, template, {})


@login_required
def view_404(request, exception):
    template = "errors/404.html"
    return render(request, template, {})


@login_required
def view_500(request):
    template = "errors/500.html"
    return render(request, template, {})


@login_required
def expense_table_data(request):
    user_expenses = Expense.objects.filter(owner=request.user)[:5]
    expenses_data = []

    for expense in user_expenses:
        new_expense = {
            'amount': float(expense.amount),
            'content': expense.content,
            'category': expense.category,
            'source': expense.source,
            'date': str(expense.date),

        }
        expenses_data.append(new_expense)

    return JsonResponse({'expenses': expenses_data})


@login_required
def statistics_table_data(request):
    statistics = Expense.objects.get_statistics(request.user)
    print(statistics['max_expense'].amount)
    stats = {
        "sum_expense": float(statistics['sum_expense']),
        'max_expense': float(statistics['max_expense'].amount),
        "max_expense_content": statistics['max_expense_content'],
        "min_expense": float(statistics['min_expense'].amount),
        "min_expense_content": statistics['min_expense_content'],
        "biggest_category_expenditure": statistics['biggest_category_expenditure'],
        "smallest_category_expenditure": statistics['smallest_category_expenditure'],
        "monthly_percentage_diff": float(statistics['monthly_percentage_diff']),
        "monthly_expense_average": float(statistics['monthly_expense_average']),
        "daily_expense_average": float(statistics['daily_expense_average']),
        "curr_month_expense_sum": float(statistics['curr_month_expense_sum']),
        "one_month_ago_expense_sum": float(statistics['one_month_ago_expense_sum']),
    }
    return JsonResponse(stats)


@login_required
def line_chart_data(request):
    user_expenses = Expense.objects.filter(owner=request.user)

    page = request.GET.get("page", 1)
    paginator = Paginator(user_expenses, 15)

    try:
        expenses = paginator.page(page)
    except PageNotAnInteger:
        expenses = paginator.page(1)
    except EmptyPage:
        expenses = paginator.page(paginator.num_pages)

    dates = [exp.date for exp in expenses]
    dates = [utils.reformat_date(date, "%d' %b") for date in dates]
    dates.reverse()

    amounts = [round(float(exp.amount), 2) for exp in expenses]
    amounts.reverse()

    chart_data = {}

    for i in range(len(dates)):
        if dates[i] not in chart_data:
            chart_data[dates[i]] = amounts[i]
        else:
            chart_data[dates[i]] += amounts[i]
    return JsonResponse(chart_data)


@login_required
def total_expenses_pie_chart_data(request):
    user_expenses = Expense.objects.filter(owner=request.user)

    chart_data = {}
    for exp in user_expenses:
        if exp.category not in chart_data:
            chart_data[exp.category] = float(exp.amount)
        else:
            chart_data[exp.category] += float(exp.amount)

    for category, amount in chart_data.items():
        chart_data[category] = round(amount, 2)
    return JsonResponse(chart_data)


@login_required
def monthly_expenses_pie_chart_data(request):
    user_expenses = Expense.objects.filter(owner=request.user)

    month_num = utils.get_month_num()
    monthly_expenses = user_expenses.filter(date__month=month_num)

    chart_data = {}
    for exp in monthly_expenses:
        if exp.category not in chart_data:
            chart_data[exp.category] = float(exp.amount)
        else:
            chart_data[exp.category] += float(exp.amount)

    for category, amount in chart_data.items():
        chart_data[category] = round(amount, 2)
    return JsonResponse(chart_data)


@login_required
def expenses_by_month_bar_chart_data(request):
    user_expenses = Expense.objects.filter(owner=request.user)
    current_year = utils.get_year_num()
    last_year = current_year - 1

    last_year_month_expenses = utils.get_yearly_month_expense_data(
        last_year, user_expenses
    )
    current_year_month_expenses = utils.get_yearly_month_expense_data(
        current_year, user_expenses
    )
    chart_data = {**last_year_month_expenses, **current_year_month_expenses}
    return JsonResponse(chart_data)


@login_required
def expenses_by_week_bar_chart_data(request):
    weeks = ["current week", "last week", "2 weeks ago", "3 weeks ago"]
    weeks.reverse()

    expenses = [
        Expense.objects.get_weekly_expense_sum(request.user),
        Expense.objects.get_weekly_expense_sum(request.user, -1),
        Expense.objects.get_weekly_expense_sum(request.user, -2),
        Expense.objects.get_weekly_expense_sum(request.user, -3),
    ]
    expenses.reverse()

    chart_data = {}
    for i, week in enumerate(weeks):
        chart_data[week] = expenses[i]
    return JsonResponse(chart_data)


@login_required
def add_testuser_data(request):
    user = str(request.user)
    if user == "testuser1" or user == "testuser3":
        req_post_dict = dict(request.POST)
        expenses_str_dict = req_post_dict["expenses"][0]
        expenses = json.loads(expenses_str_dict)

        Expense.objects.create_test_expenses(request.user, expenses)
        return redirect("expenses:home")


@login_required
def delete_testuser_data(request):
    user = str(request.user)

    if user == "testuser1" or user == "testuser3":
        Expense.objects.delete_testuser_expenses(request)
        Expense.objects.delete_testuser_budget(request)

        testusers_to_delete = User.objects.exclude(username="testuser1").exclude(
            username="testuser3"
        )
        testusers_to_delete.delete()

        return redirect("expenses:home")
    else:
        print(
            "Not allowed to delete the expenses or budget of any user other than testuser1 and testuser3"
        )
        return redirect("expenses:home")
