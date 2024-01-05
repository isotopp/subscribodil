import csv
import errno
import functools
import os
import signal
import time

from typing import Optional
import click
from dotenv import load_dotenv
from mastodon import Mastodon, MastodonError
from mastodon.utility import AttribAccessDict

TIMEOUT_VALUE=30

class TimeoutError(Exception):
    pass


def timeout(seconds=30, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wrapper

    return decorator


def log_error(error_reason: str, row: list, writer: csv.DictWriter) -> None:
    name = row['Account address']
    print(f"{name}: {error_reason}")
    row['error_reason'] = error_reason
    writer.writerow(row)
    return


@timeout(TIMEOUT_VALUE)
def follow(mastodon: Mastodon, account: AttribAccessDict) -> Optional[str]:
    """ Issue a follow request for this account to Mastdon,
        return True, if successful.
    """
    account_id = account['id']
    acct = account['acct']
    try:
        print(f"Following {acct} ({account_id})")
        mastodon.account_follow(account_id)
    except MastodonError as e:
        result = f"error following {acct}: {e}"
        print(result)
        return result

    return None


@timeout(TIMEOUT_VALUE)
def add_to_list(mastodon: Mastodon, list_id: int, account: AttribAccessDict) -> Optional[str]:
    account_id = account['id']
    acct = account['acct']

    try:
        print(f"Add {acct} to list")
        mastodon.list_accounts_add(list_id, account_id)
    except MastodonError as e:
        # they already are in the list
        if 422 in e.args:
            print(f"Account {acct} already in list.")
            return None  # this is not an error
        else:
            # other things went wrong
            result = f"Error adding to list: {acct}: {e}"
            print(result)
            return result

    return None


def process_file(mastodon: Mastodon, list_id: int, source_filename: str, retry_filename: str):
    """process a csv file with infosec people and follow them,
    then subscribe them to the list indicated. This allows us to
    suppress them in the main stream, if we are so inclined.
    """

    # write to retry filename on error. The format is the same as for the
    # input filename, allowing us to rename the file for a second run
    with (open(source_filename, mode="r", newline="", encoding="utf-8") as file,
          open(retry_filename, mode="w", newline="", encoding="utf-8") as retry_file):
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        fieldnames.append('error_reason')
        writer = csv.DictWriter(retry_file, fieldnames=reader.fieldnames)
        writer.writeheader()

        # for each line, do the thing,
        # then wait a bit as to not trigger rate limiting
        counter = 0
        for row in reader:
            name = row['Account address']
            print(f"{counter}: Working on: {name}")

            account = mastodon.account_search(name, limit=1)
            if len(account) < 1:
                log_error("account not found", row, writer)
                continue

            account = account[0]
            try:
                error = follow(mastodon, account)
                if error:
                    log_error(error, row, writer)
                    continue
            except TimeoutError:
                log_error("timeout", row, writer)
                continue

            try:
                error = add_to_list(mastodon, list_id, account)
                if error:
                    log_error(error, row, writer)
                    continue
            except TimeoutError:
                log_error("timeout", row, writer)

            print()
            counter += 1
            time.sleep(1)


def get_app(client_key: Optional[str] = None,
            client_secret: Optional[str] = None,
            access_token: Optional[str] = None,
            api_base_url: Optional[str] = None) -> Mastodon:
    """ Get a mastodon object to communicate with the server.
        All parameters are optional, in which case we load things from a dotenv file or from
        environment variables.

        Environment variables (and dotenv entries) are CLIENT_KET, CLIENT_SECRET,
        ACCESS_TOKEN, API_BASE_URL and REQUEST_TIMEOUT.
    """
    global TOTAL_TIMEOUT

    load_dotenv()
    if client_key is None:
        client_key = os.getenv("CLIENT_KEY")
    if client_secret is None:
        client_secret = os.getenv("CLIENT_SECRET")
    if access_token is None:
        access_token = os.getenv("ACCESS_TOKEN")
    if api_base_url is None:
        api_base_url = os.getenv("API_BASE_URL")

    mastodon = Mastodon(
        client_id=client_key,
        client_secret=client_secret,
        access_token=access_token,
        api_base_url=api_base_url,
    )

    return mastodon


def get_list_id(mastodon: Mastodon, list_name: str) -> int:
    """ Get the list_id for the mastdon list we want to work with.
        The list name is optional. If None, we use "Infosec".
        If the list does not exist, we create it.

        Needs an appropriately permissioned mastdon object to work with.
    """

    # get all lists and check if we already have the one we want.
    lists = mastodon.lists()
    list_id = next((list_["id"] for list_ in lists if list_["title"] == list_name), None)
    if list_id is None:
        list_id = mastodon.list_create(list_name)["id"]

    return int(list_id)


@click.command()
@click.option('--list-name', default='Infosec', show_default=True,
              help='The name of the list to subscribe these people to.')
@click.option('--file', default="mastodon_infosec_import.csv", show_default=True, help='The source csv file.')
@click.option('--retry-file', default="retry.csv", show_default=True, help="The file to write failed accounts to.")
def main(list_name: str, file: str, retry_file: str) -> None:
    mastodon = get_app()
    list_id = get_list_id(mastodon, list_name)
    process_file(mastodon, list_id, file, retry_file)


if __name__ == "__main__":
    main()
