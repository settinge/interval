utility = utility(event)
overview_soup = utility.post_login()

if event.is_interval_usage:
            overview.switch_and_validate_account_number(utility, overview_soup)
            response = interval_usage.IntervalUsage(utility).get_account_data()
