import uuid
import datetime
import base64
import json
import regex
from datetime import timedelta
from scraper_lib import errors
from interval_data import IntervalData
from scraper_lib.interval_details import IntervalDetails


class IntervalUsage:
    def __init__(self, utility):
        self.event = utility.event
        self.session = utility.session
        self.account_number = utility.account_number
        self.opower_account_number = self.account_number[:-3].ljust(9, "0")
        self.opower_base_url = "https://utility.opower.com/ei/edge/apis"
        self.prepare_payload_and_authorize()

    def prepare_payload_and_authorize(self):
        state_dict = {}
        client_id = "a7a6b7dd-a87b-464e-96cf-bd3098bb857d"
        state = str(uuid.uuid1())
        nonce = str(uuid.uuid1())
        client_request_id = str(uuid.uuid1())
        date_timestamp = int(datetime.datetime.now().timestamp())
        state_dict["id"] = state
        state_dict["ts"] = date_timestamp
        state_dict["method"] = "silentInteraction"
        state_dict_json = json.dumps(state_dict)
        state_dict_bytes = bytes(state_dict_json, "utf-8")
        state = base64.b64encode(state_dict_bytes)
        access_token_regex = r"access_token=(?P<access_token>.*?)\&"

        auth_response = self.session.get(
            "https://login.utilityus.com/login.utilityus.com/"
            "b2c_1a_utility_convert_merge_signin/oauth2/v2.0/authorize",
            params={
                "client_id": client_id,
                "state": state,
                "nonce": nonce,
                "client-request-id": client_request_id,
                "response_type": "id_token token",
                "scope": "openid https://login.utilityus.com/"
                "opower/opower profile",
                "redirect_uri": "https://www1.utilityus.com/BlankPage.aspx",
                "client_info": 1,
                "x-client-SKU": "MSAL.JS",
                "x-client-Ver": "1.3.0",
                "sid": True,
                "prompt": "none",
                "response_mode": "fragment",
            },
        )

        access_token = regex.search(access_token_regex, auth_response.url)[
            "access_token"
        ]
        self.session.headers.update({"authorization": f"Bearer {access_token}"})

    def get_account_data(self):
        account_data = self.session.get(
            f"{self.opower_base_url}/multi-account-v1/cws/utility/customers/current",
            headers={
                "opower-selected-entities": f'["urn:external:opower:entity:id:'
                f'{self.account_number}-{self.opower_account_number}"]'
            },
            timeout=120,
            expected_errors=[403],
        )
        if account_data.status_code == 403:
            raise errors.IntervalNotAvailable("No active accounts found")

        self.validate_and_verify_account(account_data)
        return self.get_interval_details()

    def validate_and_verify_account(self, account_data):
        account_number_list = []
        self.utility_account_uuid = None
        for utility_account in account_data.json()["utilityAccounts"]:
            account_number_list.append(utility_account["utilityAccountId"].rstrip("-E"))
            if utility_account["utilityAccountId"].rstrip("-E") == self.account_number:
                self.utility_account_uuid = utility_account["uuid"]

        if (
            self.account_number not in account_number_list
            or not self.utility_account_uuid
        ):
            raise errors.AccountNumberValidationError

        self.customer_uuid = account_data.json()["uuid"]

    def get_interval_details(self):
        params = {
            "aggregateType": "hour",
            "includeEnhancedBilling": "false",
            "includeMultiRegisterData": "false",
        }
        details = []
        self.set_interval_query_dates()
        while self.begin_date < self.end_date:
            params["startDate"] = self.begin_date.strftime("%Y-%m-%d")
            params["endDate"] = (self.begin_date + timedelta(days=30)).strftime(
                "%Y-%m-%d"
            )
            hourly_usage = self.session.get(
                f"{self.opower_base_url}/DataBrowser-v1/cws/utilities/"
                f"utility/utilityAccounts/{self.utility_account_uuid}/reads",
                params=params,
                headers={
                    "opower-selected-"
                    "entities": f'["urn:opower:customer:uuid:{self.customer_uuid}"]'
                },
                expected_errors=[403, 401],
            )
            if hourly_usage.status_code in [403, 401]:
                raise errors.IntervalNotAvailable

            for usage in hourly_usage.json()["reads"]:
                details.append(
                    IntervalData(
                        {
                            "record_start_date_time": usage["endTime"],
                            "record_end_date_time": usage["startTime"],
                            "kwh": usage["consumption"]["value"],
                            "cost": usage["providedCost"],
                        }
                    ).data()
                )

            self.begin_date = self.begin_date + datetime.timedelta(days=30)
        interval_details = IntervalDetails(
            event=self.event,
            records=details,
            extra_fields={"timezone": "America/New_York"},
        )
        return interval_details.data()

    def set_interval_query_dates(self):
        if not self.event.is_interval_ready():
            raise errors.NoNewIntervalError

        # limiting begin date to day after DST
        # since we don't have enough historical data
        self.begin_date = datetime.datetime(2021, 3, 15)
        # leaving here for when we have historical data
        # after DST

        # self.begin_date = (
        #     self.event.interval_start_date
        #     if self.event.interval_start_date
        #     else datetime.datetime.today() - timedelta(days=365)
        # )
        self.end_date = (
            self.event.interval_end_date
            if self.event.interval_end_date is not None
            else datetime.datetime.today() - datetime.timedelta(days=1)
        )
