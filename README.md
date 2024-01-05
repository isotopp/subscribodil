# Subscribodil

Subscribodil uses the Mastodon API to subscribe people to your account and then add them to a list.

## Installation

```bash
# Clone the repo
git clone https://github.com/isotopp/subscribodil.git
# change into the repo
cd subscribodil
# set up a virtual environment
python3 -mvenv mvenv
# activate it
source venv/bin/activate
# update it
pip install -U pip wheel
# install dependencies
pip install -r requirements.txt
# test it
python subscribodil.py --help
```

## Usage

```bash
python subscribodil.py --help
Usage: subscribodil.py [OPTIONS]

Options:
  --list-name TEXT   The name of the list to subscribe these people to.
                     [default: Infosec]
  --file TEXT        The source csv file.  [default:
                     mastodon_infosec_import.csv]
  --retry-file TEXT  The file to write failed accounts to.  [default:
                     retry.csv]
  --help             Show this message and exit.
```

Substitute your mastodon instance name for "chaos.social":
1. Go to https://chaos.social/settings/applications and create a new application subscribodil.
2. Give it "read write:follows write:lists follow" permissions.
3. Grab the credentials from the subscribodil application you just created and put them into a .env file.
   ```
   CLIENT_KEY=redacted
   CLIENT_SECRET=redacted
   ACCESS_TOKEN=redacted
   API_BASE_URL=https://chaos.social <- your instance here
   ```
4. Download https://github.com/cstromblad/infosec_mastodon/blob/main/mastodon_infosec_import.csv
   from https://github.com/cstromblad/infosec_mastodon/tree/main
5. Run it with the venv acticated:
   ```
   source venv/bin/activate
   python main.py
   ```

# What is a Subscribodil?

It is a cute little crocodile that manages your lists for you.

![](subscribodil.png)
