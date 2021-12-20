#!/usr/bin/env python3

import sys
import pprint
import csv
from simple_term_menu import TerminalMenu
import os
import subprocess
import datetime
import pathlib
from .basicmenu import BasicMenu
from .prompter import Prompter


#configuration
kb_threshold = 1000   # ignore results for files with size-in-k less than this value
pstats = pathlib.Path.home() / '.du_stats'

pstats.mkdir(parents=True, exist_ok=True)

########################################################################################


########################################################################################


class MainMenu(BasicMenu):
  TITLE = "Main Menu:"
  SUDO = True
  MAIN = None
  REF = None

  def menuitem_01_toggle_sudo(self):
    """Toggle Sudo"""
    self.SUDO = not self.SUDO
    self.show_settings()

  def menuitem_02_scan_currend_directory(self):
    """Scan current directory to file"""
    pwd = pathlib.Path().resolve()
    suffix = str(pwd).replace('/', '-')
    if suffix == '-':
      suffix += 'root'
    output_file = pstats / f'du-{datetime.datetime.now():%Y-%m-%d-%H%M}{suffix}.txt'
    sudo_cmd = "sudo " if self.SUDO else ""
    du_cmd = f'{sudo_cmd}du -akx "{pwd}" 2>/dev/null | awk -F "\t" \'$1>{str(kb_threshold)}\' > {output_file}'
    print(du_cmd)
    # sys.exit()
    print(f'Scanning/saving current directory disk usage stats...    ({pwd})')
    subprocess.run(du_cmd, shell=True)
    self.MAIN = output_file.name
    self.show_settings()

  def menuitem_03_choose_main(self):
    """Choose main stats file"""
    stats_file = Prompter.get_multichoice("Select the main/primary stats file:", self.get_stats_files(reverse_sort=True))
    self.MAIN = stats_file
    self.show_settings()

  def menuitem_04_choose_ref(self):
    """Choose reference stats file"""
    stats_file = Prompter.get_multichoice("Select a stats file (for comparative purposes):", self.get_stats_files(reverse_sort=True))
    self.REF = stats_file
    self.show_settings()

  def menuitem_05_show_stats(self):
    """Show statistics"""
    if self.MAIN is None:
      print("ERROR: Choose a main stats file before you can show statistics ")
      return
    else:
      main_stats = self.load_du(pstats / self.MAIN)

    if self.REF is None:
      ref_stats = {}
    else:
      ref_stats = self.load_du(pstats / self.REF)

    min_level = min(main_stats.keys())
    self.show_stats(main_stats, ref_stats, min_level, next(iter(main_stats[min_level])))

  def menuitem_06_delete_stats(self):
    """Delete stats file"""
    stats_file = Prompter.get_multichoice("Select a stats file to delete:", self.get_stats_files(reverse_sort=True))

    confirmation = Prompter.get_multichoice(f"Are you sure you want to delete the '{stats_file}' stats file?", ['Yes', 'No'])
    if confirmation == 'Yes':
      (pstats / stats_file).unlink()


  def show_settings(self):
    print('Settings:')
    print(f'  sudo = {self.SUDO}')
    print(f'  main = {self.MAIN}')
    print(f'   ref = {self.REF}')
    print()

  def load_du(self, pname):
    dat = {}
    with open(pname, newline = '') as file:
      file_reader = csv.reader(file, delimiter='\t')
      for line in file_reader:
        size = int(line[0]) * 1024
        path = line[1]
        level = path.count('/')+1 if (path != '/') else 1
        if not level in dat:
          dat[level] = {}
        dat[level][path] = size
      return dat

  def get_stats_files(self, reverse_sort=False):
    try:
      job_folders = tuple(sorted(pstats.glob('du-*.txt'), reverse=reverse_sort))     # search for du stats files
      return [folder.name for folder in job_folders]
    except:
      return []


  def show_stats(self, main, ref, level, prefix=''):

    def get_size_safe(x, pname):
      if pname in x:
        return x[pname]
      else:
        return 0

    def sizeof_fmt(num, suffix="B"):
        for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
            if abs(num) < 1024.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Yi{suffix}"

    def sizeof_fmt_dec(num, suffix="B"):
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if abs(num) < 1000.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1000.0
        return f"{num:.1f}Yi{suffix}".trim()


    if level in main:
      main_filt = dict(filter(lambda elem: elem[0].startswith(prefix), main[level].items()))
    else:
      main_filt = {}

    if level in ref:
      ref_filt = dict(filter(lambda elem: elem[0].startswith(prefix), ref[level].items()))
    else:
      ref_filt = {}

    combined_keys = list(set(main_filt.keys()) | set(ref_filt.keys()))

    combined = {}
    for key in combined_keys:
      item = {}

      item['name'] = os.path.basename(key)
      item['main_exists'] = key in main_filt
      item['ref_exists'] = key in ref_filt

      item['main_size'] = get_size_safe(main_filt, key)
      item['ref_size'] = get_size_safe(ref_filt, key)
      item['diff_size'] = item['main_size'] - item['ref_size']
      item['sort_size'] = max(item['main_size'], item['ref_size'], abs(item['diff_size']))

      item['main_size_fmt'] = sizeof_fmt_dec(item['main_size'])
      item['diff_size_fmt'] = sizeof_fmt_dec(item['diff_size'])
      if not item['diff_size_fmt'].startswith('-'):           # prepend '+' for positive diffs
        item['diff_size_fmt'] = '+' + item['diff_size_fmt']
      if item['diff_size_fmt'] == '+0.0B':                    # show zero as blank
        item['diff_size_fmt'] = ''


      if not item['main_exists']:
        item['name'] += '     ** MISSING **'
        item['main_size'] = "-"

      if not item['ref_exists']:
        item['diff_size_fmt'] = '-'

      combined[key] = item

    tmp = list(reversed(sorted(combined.items(), key=lambda x:x[1]['sort_size'])))
    combined = dict(tmp[:20])
    values       = [k                       for (k,v) in combined.items()]
    descriptions = [f"  {v['main_size_fmt']: <10} {v['diff_size_fmt']: <10} {v['name']}" for (k,v) in combined.items()]

    while True:
      # show menu and process results
      menu_entry_index = TerminalMenu(descriptions, title=prefix).show()
      if (menu_entry_index is None):
        return None
      value = values[menu_entry_index]
      description = descriptions[menu_entry_index]

      # print(f' {value}')

      self.show_stats(main, ref, level+1, value)


def main():
    MainMenu().show()

