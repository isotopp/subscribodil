import csv
import os
from mastodon import Mastodon, MastodonError
from dotenv import load_dotenv
import time


def process_file(filename, mastodon, list_id, retry_filename):
    """process a csv file with info sec people and follow them,
    then sunscribe them to the list Infosec. This allows us to
    suppress them in the main stream, if we are so inclined.
    """

    # write to retry filename on error. The format is the same as for the
    # input filename, allowing us to rename the file for a second run
    with open(filename, mode="r", newline="", encoding="utf-8") as file, open(
        retry_filename, mode="w", newline="", encoding="utf-8"
    ) as retry_file:
        reader = csv.DictReader(file)
        writer = csv.DictWriter(retry_file, fieldnames=reader.fieldnames)
        writer.writeheader()

        # for each line, do the thing,
        # then wait a bit as to not trigger rate limiting
        counter = 0
        for row in reader:
            try:
                print(f"{counter}: Working on: {row['Account address']}")
                account = mastodon.account_search(row["Account address"], limit=1)
                if account:
                    # follow them
                    try:
                        print("Following...")
                        mastodon.account_follow(account[0]["id"])
                    except MastodonError as e:
                        print(f"error following {row['Account address']}: {e}")
                        writer.writerow(row)
                        continue

                    # add them to list
                    print("Add to List...")
                    try:
                        mastodon.list_accounts_add(list_id, account[0]["id"])
                    except MastodonError as e:
                        if 422 in e.args:
                            print(f"Account {row['Account address']} already in list.")
                        else:
                            print(
                                f"cannot add Account {row['Account address']} to list: {e}"
                            )
                        writer.writerow(row)
                else:
                    # we cannot find them
                    print(f"can't find account {row['Account address']}")
                    writer.writerow(row)

            # something else did not work
            except Exception as e:
                print(f"error working on {row['Account address']}: {e}")
                writer.writerow(row)
            print()
            counter += 1
            time.sleep(1)


# Load an environment
load_dotenv()


# dotenv serves fake environment to getenv()
client_key = os.getenv("CLIENT_KEY")
client_secret = os.getenv("CLIENT_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
api_base_url = os.getenv("API_BASE_URL")
request_timeout = int(os.getenv("REQUEST_TIMEOUT"))

print(f"{api_base_url=} {request_timeout=}")
# Build the client object
mastodon = Mastodon(
    client_id=client_key,
    client_secret=client_secret,
    access_token=access_token,
    api_base_url=api_base_url,
    request_timeout=request_timeout,
)

# Ensure we have a list and know the id
list_name = "Infosec"
list_id = None
lists = mastodon.lists()

for list_ in lists:
    if list_["title"] == list_name:
        list_id = list_["id"]
        break

if list_id is None:
    list_id = mastodon.list_create(list_name)["id"]

retry_filename = "retry.txt"
process_file("infosec.txt", mastodon, list_id, retry_filename)
