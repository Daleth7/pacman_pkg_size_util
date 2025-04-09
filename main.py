#!/bin/python3

from argparse import ArgumentParser
from typing import List, Mapping, Tuple

from textual.app import App, ComposeResult
from textual.widgets import Tree

from PkgInfo import PkgInfo
from query_pkg import query_pkg_info_list

# Check for repeated dependency names and invalid names.
# Ignore:
#   - Repeats
#   - Library files (usually provided by other dependencies)
def is_invalid(dep : str, mask_list : List[str]) -> bool:
    return dep in mask_list      \
        or dep.startswith('lib') \
        or ('.so' in dep)

def query_list(dep_list : List[str], mask_list : List[str]) -> Tuple[List[PkgInfo]|None,List[str]]:
    if dep_list[0] == 'None':
        return None, mask_list

    filtered_dep_list = [dep for dep in dep_list if not is_invalid(dep, mask_list)]
    if len(filtered_dep_list) < 1:
        mask_list += dep_list
        return None, mask_list
    new_dep_list = query_pkg_info_list(*filtered_dep_list)
    mask_list += dep_list
    for dep in new_dep_list:
        if dep.dependencies is None: continue
        dep.dependencies, mask_list = query_list(dep.dependencies, mask_list)
        mask_list.append(dep.name)
    return new_dep_list, mask_list





parser = ArgumentParser(description = 'Utility to look up total package size including its dependencies.')
parser.add_argument( '-w', '--which',
                     default = 'install',
                     choices = ['download', 'install'],
                     help = 'Which size to show.'
                     )
parser.add_argument( '-d', '--depth', '--max-depth',
                     type = int,
                     help = 'Maximum depth to show.'
                     )
parser.add_argument( '-a', '--expand-all',
                     action = 'store_true',
                     dest = 'expandall',
                     help = 'Expand all levels of the tree.'
                     )
parser.add_argument('package', nargs = '+', help = 'Package name or list of pacakge names.')
args = parser.parse_args()

pkg_list = query_pkg_info_list(*args.package)
if pkg_list is None:
    raise ValueError(f'Could not query info. for {args.package}')
mask_list = ['sh']
total_size = 0.0
for pkg in pkg_list:
    pkg.dependencies, mask_list = query_list(pkg.dependencies, mask_list)
    mask_list.append(pkg.name)
    pkg.update_sizes()
    total_size += pkg.total_size_raw(args.which)





class SizeTreeApp(App):
    def compose(self) -> ComposeResult:
        tree : Tree[str] = Tree(f'{PkgInfo.format_size(total_size)} | Total')
        for pkg in pkg_list:
            SizeTreeApp.generate_dep_branch(tree.root, pkg, args.depth)
        if args.expandall:
            tree.root.expand_all()
        else:
            tree.root.expand()
        yield tree

    def generate_dep_branch(tree_node, pkg_info : PkgInfo, depth : int) -> None:
        if (depth is not None) and (depth < 1): return
        add_method = tree_node.add_leaf if pkg_info.dependencies is None else tree_node.add
        branch = add_method(f'{pkg_info.total_size(args.which)} | {pkg_info.name}')
        if pkg_info.dependencies is not None:
            branch.add_leaf(f'{PkgInfo.format_size(pkg_info.sizes[f"{args.which} (self)"])} | self')
            dep_sorted_list = sorted(pkg_info.dependencies, key = lambda p:p.total_size(args.which))
            for dep in dep_sorted_list:
                SizeTreeApp.generate_dep_branch(branch, dep, None if depth is None else (depth-1))





app = SizeTreeApp()
app.run()