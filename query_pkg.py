provides_keyname = 'Provides'
req_dep_keyname = 'Depends On'
opt_dep_keyname = 'Optional Deps'
size_keyname = 'Size'

from typing import List, Mapping, Any
import re

import subprocess
from PkgInfo import PkgInfo

import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)

log = logging.getLogger("rich")

def _process_val_raw_str(key : str, raw : str) -> Any:
    if raw == 'None':
        return None

    if key == opt_dep_keyname:
        # Get the optional dependency package name
        name_search = re.search(r' *(.*?):', raw)
        return [name_search.group(1) if name_search else raw]
    elif key in [req_dep_keyname, provides_keyname]:
        # Package names are seperated with two spaces.
        raw = [pkg_name.strip() for pkg_name in raw.split('  ')]
        # Some packages might specify a version after a "=", "<=", "=>", "<", or ">".
        # So filter out the version #.
        filtered = [(v, re.search(r'^(.*?)(?:<=|>=|<|>|=)', v)) for v in raw]
        return [result.group(1) if result else v for v, result in filtered]
    elif size_keyname in key:
        factor_exp = None
        if 'GiB' in raw:
            factor_exp = 30
        elif 'MiB' in raw:
            factor_exp = 20
        elif 'KiB' in raw:
            factor_exp = 10
        else:
            raise ValueError(f'Could not parse size for "{key}" package! Size value = "{raw}"')
        # Remove the unit suffix and convert to bytes
        factor = 2**factor_exp
        return factor*float(re.search(r'^(.*?) *(?:KiB|MiB|GiB)', raw).group(1))

    # Nothing to process
    return raw

def _process_raw_query(query_raw : List[str]) -> PkgInfo | None:
    query_results : Mapping[str, str | List[str]] = {}
    for line in query_raw:
        # Assume there's a colon with spaces separating the key name
        # and the key's value. Extract the key and value.
        # For example, "abc   : def" --> "abc" and "def"
        split_result = re.search(r'^(.*?)  *: *(.*)', line)
        if split_result is None:
            if opt_dep_keyname not in query_results:
                raise ValueError(f'Could not process line from query! Line: "{line}"')
            # An extra line under "Optional Deps."
            # Below is an example output of package info.
            # Optional Deps  : pkg1: pkg description
            #                  pkg2: pkg description
            #                  pkg3: pkg description
            name_search = re.search(r' *(.*?):', line)
            query_results[opt_dep_keyname].append(name_search.group(1) if name_search else line)
            continue
        else:
            key = split_result.group(1)
            val = _process_val_raw_str(key, split_result.group(2))

            query_results[key] = val

    return PkgInfo(**query_results)

def query_pkg_info(package : str) -> PkgInfo | None:
    process_result = subprocess.run(['pacman', '-Si', package], text = True, check = True, capture_output = True)

    # When passing, ignore last line as it is blank.
    return _process_raw_query(process_result.stdout.splitlines()[:-1])

def try_query_pkg_info(package : str, default : PkgInfo) -> PkgInfo:
    try:
        return query_pkg_info(package)
    except subprocess.CalledProcessError:
        log.warn(f'Failed to query info for [bold red blink]{package}[/]. Assuming package is provided by something else.')
        return default

def query_pkg_info_list(package : str, *package_list : List[str]) -> List[PkgInfo | None]:
    try:
        process_result = subprocess.run(['pacman', '-Si', package, *package_list], text = True, check = True, capture_output = True)
    except subprocess.CalledProcessError as e:
        log.info('Querying info. for list of packages failed. Trying one at a time.')
        return [try_query_pkg_info(pkg, PkgInfo.make_blank(f'{pkg} ([#666666]no info[/])')) for pkg in [package, *package_list]]

    # Insert blank line at the end since pacman adds an extra line between
    # each result. This keeps the format consistent for later splitting.
    raw_output = [*process_result.stdout.splitlines(), '']
    count = len(raw_output)

    # Find the position of each line that starts a new result.
    # Each new result should start with a "Repository" line.
    # Note: Cannot assume # of lines for each result is the
    # same since the number of dependencies may be different.
    idxs = [*[i for i, val in enumerate(raw_output) if 'Repository' in val], -1]
    ranges = [(idxs[i],idxs[i+1]) for i in range(len(idxs)-1)]

    return [_process_raw_query(raw_output[start:stop-1]) for start, stop in ranges]

def query_installed_pkgs() -> List[str]:
    process_result = subprocess.run(['pacman', '-Qq'], text = True, check = True, capture_output = True)
    return [*process_result.stdout.splitlines()]