import argparse
import json
import logging
import os
import requests
import subprocess
import sys

from fusesoc.config import Config
from fusesoc.coremanager import DependencyError
from fusesoc.fusesoc import Fusesoc

logger = logging.getLogger(__name__)

def _get_core(cm, name):
    matches = set()
    if not ":" in name:
        for core in cm.get_cores():
            (v, l, n, _) = core.split(":")
            if n.lower() == name.lower():
                matches.add(f"{v}:{l}:{n}")
        if len(matches) == 1:
            name = matches.pop()
        elif len(matches) > 1:
            _s = f"'{name}' is ambiguous. Potential matches: "
            _s += ", ".join(f"'{x}'" for x in matches)
            logger.error(_s)
            exit(1)

    core = None
    try:
        core = cm.get_core(name)
    except RuntimeError as e:
        logger.error(str(e))
        exit(1)
    except DependencyError as e:
        logger.error(
            f"{name!r} or any of its dependencies requires {e.value!r}, but "
            "this core was not found"
        )
        exit(1)
    except SyntaxError as e:
        logger.error(str(e))
        exit(1)
    return core

def guess_provider(core):
    guess = {"found": False}
    cmd = ["git", "remote", "-v"]
    res = subprocess.run(cmd, capture_output=True, cwd=core.core_root).stdout.decode("utf-8").strip()
    lines = res.splitlines()
    if len(lines) < 1:
        return guess
    fetchlines = list(filter(lambda s: s.endswith("(fetch)"), lines))
    if not fetchlines:
        return guess
    # Pick first fetch line
    fetchline = fetchlines[0]
    if "https://github.com" in fetchline:
        guess["name"] = "github"
        comps = fetchline.split("/")
        user = comps[3]
        repo = comps[4]
        repo = repo[: len(repo) - len("(fetch)")].strip()
    elif "git@github.com" in fetchline:
        guess["name"] = "github"
        _userrepo = fetchline.split(":")[1].split()[0].split('/')
        user = _userrepo[0]
        repo = _userrepo[1].removesuffix(".git")

    cmd = ["git", "log", "-n", "1"]
    res = (
        subprocess.run(cmd, capture_output=True, cwd=core.core_root)
        .stdout.decode("utf-8")
        .strip()
        .splitlines()[0]
    )
    print(res)
    comps = res.split(" ")
    if (len(comps) >= 2) and (comps[0] == "commit"):
        version = comps[1]
    else:
        version = ""
    guess[
        "yaml"
    ] = """provider:
  name : {}
  user : {}
  repo : {}
  version : {}
""".format(
        guess["name"], user, repo, version
    )
    guess["found"] = True
    return guess


def core_publish(fs, args):
    core = _get_core(fs, args.core)
    uri = args.server
    sigfile = core.core_file + ".sig"
    if core.provider:
        provider_name = type(core.provider).__name__.lower()
        if not provider_name in ["github"]:
            logger.error(
                "The provider for this core is '"
                + provider_name
                + "' which is not yet supported for publishing."
            )
            return False
    if core.provider == None:
        provider_info = guess_provider(core)
        if provider_info["found"] == False:
            logger.error(
                "No provider is given in core file or guessable from current project.  Aborting."
            )
            return False
        if provider_info["name"] != "github":
            logger.error(
                "No provider is given in core file, and the current project appears to not be using a compatible provider, which is needed for publishing."
            )
            return False
        logger.info(
            "No provider is given in core file, but the current project seems to be on github."
        )
        if not args.autoprovider:
            logger.info(
                "The following provider section can be added to the core file if the --autoprovider flag is given to this command."
            )
            print(provider_info["yaml"])
            return False
        logger.info("Adding the following provider section to the core file.")
        print(provider_info["yaml"])
        cf = open(core.core_file, "ab")
        cf.write(("\n" + provider_info["yaml"] + "\n").encode("utf-8"))
        cf.close()
        logger.info("Now retry publishing.")
        return False

    logger.info("Core provider: " + provider_name)
    logger.info("Publish core file: " + core.core_file)
    fob_core = open(core.core_file, "rb")
    body = {"core_file": fob_core}
    fob_sig = None
    if os.path.exists(sigfile):
        logger.info("and signature file: " + sigfile)
        fob_sig = open(sigfile, "rb")
        body["signature_file"] = fob_sig
    else:
        logger.info("(without signature file)")
        sf_data = None
    logger.info("to api at: " + uri)
    if args.yes:
        logger.info("without confirmation")
    else:
        c = input("Confirm by typing 'yes': ")
        if c != "yes":
            logger.info("Aborted.")
            return False

    target = uri + "/api/v1/publish/"
    logger.debug("POST to " + target)
    res = requests.post(target, files=body, allow_redirects=True)
    if res.ok:
        logger.info(f"Core {core.name} published successfully")
    else:
        if res.status_code == 409:
            content = json.loads(res.content)
            logger.error(content["error"])
        else:
            logger.error("Request returned http result", res.status_code, res.reason)
            err = json.loads(res.content)
            print(json.dumps(err, indent=4))
    res.close()
    fob_core.close()
    if fob_sig:
        fob_sig.close()

def parse_args(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cores-root",
        help="Add additional directories containing cores",
        default=[],
        action="append",
    )
    parser.add_argument("--config", help="Specify the config file to use")

    parser.add_argument(
        "core", help="Name of the core to publish"
    )

    parser.add_argument(
        "server", help="FuseSoC Package Database Server"
    )
    parser.add_argument(
        "--yes", help="Skip confirmation", action="store_true"
    )
    parser.add_argument(
        "--autoprovider",
        help="Automatically add provider section if missing and possible to guess",
        action="store_true",
    )

    return parser.parse_args(argv)

def main():
    args = parse_args(sys.argv[1:])
    if not args:
        exit(0)
    logging.basicConfig(level=logging.INFO)

    config = Config(args.config)
    setattr(config, "args_cores_root", args.cores_root)

    fs = Fusesoc(config)
    core_publish(fs, args)
