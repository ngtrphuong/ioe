"""
Date and time utility functions.
"""
from datetime import datetime, time, timedelta, date
import calendar


def get_period_boundaries(date, period='day'):
    """
    Get the start and end datetime for a specific period.
    
    Args:
        date: The date to get boundaries for
        period: 'day', 'week', 'month' or 'year'
        
    Returns:
        tuple: (start_datetime, end_datetime)
    """
    if period == 'day':
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
    elif period == 'week':
        # Start of week (Monday)
        start_dt = datetime.combine(date - timedelta(days=date.weekday()), time.min)
        # End of week (Sunday)
        end_dt = datetime.combine(start_dt.date() + timedelta(days=6), time.max)
    elif period == 'month':
        # Start of month
        start_dt = datetime.combine(date.replace(day=1), time.min)
        # End of month - go to next month and go back one day
        if date.month == 12:
            next_month = date.replace(year=date.year+1, month=1, day=1)
        else:
            next_month = date.replace(month=date.month+1, day=1)
        end_dt = datetime.combine(next_month - timedelta(days=1), time.max)
    elif period == 'year':
        # Start of year
        start_dt = datetime.combine(date.replace(month=1, day=1), time.min)
        # End of year
        end_dt = datetime.combine(date.replace(month=12, day=31), time.max)
    else:
        # Default to day
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        
    return (start_dt, end_dt)


def get_month_range(year, month):
    """
    Get the date range for a given year and month.
    
    Args:
        year: Year, e.g., 2023
        month: Month number, 1-12
        
    Returns:
        tuple: (start_date, end_date) first and last date of the month
    """
    # Validate inputs
    year = int(year)
    month = int(month)
    
    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12")
    
    # First day of month
    start_date = date(year, month, 1)
    
    # Last day of month (compute next month's first day then subtract one day)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return (start_date, end_date)


def get_quarter_range(year, quarter):
    """
    Get the date range for a given year and quarter.
    
    Args:
        year: Year, e.g., 2023
        quarter: Quarter number 1-4
        
    Returns:
        tuple: (start_date, end_date) first and last date of the quarter
    """
    # Validate inputs
    year = int(year)
    quarter = int(quarter)
    
    if quarter < 1 or quarter > 4:
        raise ValueError("Quarter must be between 1 and 4")
    
    # Determine month range for the quarter
    start_month = (quarter - 1) * 3 + 1  # 1, 4, 7, 10
    if quarter < 4:
        end_month = quarter * 3  # 3, 6, 9
    else:
        end_month = 12
    
    # Quarter start date
    start_date = date(year, start_month, 1)
    
    # Quarter end date (first day of next quarter minus one day)
    if end_month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, end_month + 1, 1) - timedelta(days=1)
    
    return (start_date, end_date)


def get_year_range(year):
    """
    Get the date range for a given year.
    
    Args:
        year: Year, e.g., 2023
        
    Returns:
        tuple: (start_date, end_date) first and last date of the year
    """
    # Validate input
    year = int(year)
    
    # Start date (Jan 1)
    start_date = date(year, 1, 1)
    
    # End date (Dec 31)
    end_date = date(year, 12, 31)
    
    return (start_date, end_date)


def get_date_format(period):
    """
    Return date format string based on period.
    
    Args:
        period: One of 'day', 'week', 'month', 'quarter', 'year'
        
    Returns:
        str: Date format string
    """
    formats = {
        'day': '%Y-%m-%d',
        'week': '%Y-%m-%d',
        'month': '%Y-%m',
        'quarter': '%Y-Q%q',
        'year': '%Y'
    }
    return formats.get(period, '%Y-%m-%d')


def get_date_range(start_date=None, end_date=None, period=None, days=None):
    """
    Compute a date range using multiple modes:
    1) Provide start and end dates directly
    2) Provide a named period ('today', 'yesterday', 'last_week', 'last_month', ...)
    3) Provide a number of days to look back
    
    Args:
        start_date: datetime.date or 'YYYY-MM-DD'
        end_date: datetime.date or 'YYYY-MM-DD'
        period: 'today' | 'yesterday' | 'this_week' | 'last_week' |
                'this_month' | 'last_month' | 'this_quarter' | 'last_quarter' |
                'this_year' | 'last_year'
        days: Number of days to look back
    
    Returns:
        tuple: (start_date, end_date) as datetime.date objects
    """
    today = date.today()
    
    # Handle string date inputs
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # If both start and end dates are provided, return immediately
    if start_date and end_date:
        return start_date, end_date
    
    # Calculate date range based on period
    if period:
        if period == 'today':
            return today, today
        elif period == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif period == 'this_week':
            # Monday of the current week
            monday = today - timedelta(days=today.weekday())
            return monday, today
        elif period == 'last_week':
            # Monday and Sunday of last week
            monday = today - timedelta(days=today.weekday() + 7)
            sunday = monday + timedelta(days=6)
            return monday, sunday
        elif period == 'this_month':
            # First day of this month
            first_day = date(today.year, today.month, 1)
            return first_day, today
        elif period == 'last_month':
            # First and last day of last month
            if today.month == 1:
                first_day = date(today.year - 1, 12, 1)
                last_day = date(today.year, 1, 1) - timedelta(days=1)
            else:
                first_day = date(today.year, today.month - 1, 1)
                last_day = date(today.year, today.month, 1) - timedelta(days=1)
            return first_day, last_day
        elif period == 'this_quarter':
            # First day of this quarter
            quarter = (today.month - 1) // 3 + 1
            first_day = date(today.year, (quarter - 1) * 3 + 1, 1)
            return first_day, today
        elif period == 'last_quarter':
            # First and last day of last quarter
            quarter = (today.month - 1) // 3 + 1
            if quarter == 1:
                # Q4 of the previous year
                first_day = date(today.year - 1, 10, 1)
                last_day = date(today.year, 1, 1) - timedelta(days=1)
            else:
                # Previous quarter of the current year
                first_day = date(today.year, (quarter - 2) * 3 + 1, 1)
                last_day = date(today.year, (quarter - 1) * 3 + 1, 1) - timedelta(days=1)
            return first_day, last_day
        elif period == 'this_year':
            # First day of this year
            first_day = date(today.year, 1, 1)
            return first_day, today
        elif period == 'last_year':
            # First and last day of last year
            first_day = date(today.year - 1, 1, 1)
            last_day = date(today.year, 1, 1) - timedelta(days=1)
            return first_day, last_day
    
    # Compute by number of days to look back
    if days:
        days = int(days)
        start_date = today - timedelta(days=days)
        return start_date, today
    
    # Default to today
    return today, today 