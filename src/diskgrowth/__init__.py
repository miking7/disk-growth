#!/usr/bin/env python3

import sys
import csv
import pprint
from simple_term_menu import TerminalMenu
import os
import subprocess
import datetime
import inspect
import pathlib


#configuration
kb_threshold = 1000   # ignore results for files with size-in-k less than this value
pstats = pathlib.Path.home() / '.du_stats'

pstats.mkdir(parents=True, exist_ok=True)

########################################################################################

class BasicMenu(object):
  """The BasicMenu class implements a simple TerminalMenu.

  Subclasses define menu items as functions:
    - with names starting with the "menuitem_XX_..." prefix
    - and docblocks defining the menu text
    - any function parameters are (attempted to be) fulfilled using kwargs passed to show() - ie: xxx.show(my_param='abc') --> menuitem_02_abc(my_param='abc')

  Example menu item functions:
    def menuitem_01_xyz(self):
      '''XYZ'''
      print("Do something")
    
    def menuitem_02_abc(self, my_param):
      '''ABC'''
      print("Do something")
  """


  TITLE = "BasicMenu Title:"    # replace with actual menu title in subclasses

  def menuitem_quit():
    """Quit"""
  
  def show(self, **kwargs):
    """Show / Run the menu"""
    import string

    # create menu strings from menu function docblocks
    menu_strings=[]
    for i, menu_function in enumerate(self.menu_functions):
      description = menu_function.__doc__.splitlines()[0]
      shortcut = string.ascii_lowercase[i]
      if menu_function == self.menuitem_quit:
        shortcut = "q"
      menu_strings.append(f"[{shortcut}] {description}")

    # show the menu (repeatedly until quit)
    terminal_menu = TerminalMenu(menu_strings, title=self.TITLE)    
    while True:
      menu_entry_index = terminal_menu.show()

      # alias <escape> to quit
      if menu_entry_index is None:
        menu_entry_index = self.menu_functions.index(self.menuitem_quit)

      # handle quit
      if menu_entry_index == self.menu_functions.index(self.menuitem_quit):
        return

      # handle normal selection - call the selected function
      try:
        print(f"{self.TITLE} selected '{menu_strings[menu_entry_index]}'...\n")

        # prepare function arguments (based on introspection of the selected function)
        selected_function = self.menu_functions[menu_entry_index]
        fnargs = kwargs
        sig = inspect.signature(selected_function)
        if 'kwargs' not in sig.parameters:
          fnargs = {k:v for (k,v) in fnargs.items() if k in sig.parameters}   # filter arguments when selected_function does not accept **kwargs
        
        # call the selected function
        self.menu_functions[menu_entry_index](**fnargs)
      except KeyboardInterrupt:
        print("\nCtrl-C detected.")

  @property
  def menu_functions(self):
    """The list of menu-item functions:
     - matching the 'menuitem_XX_...' pattern  (where XX is 2-digit number)
     - plus the 'menuitem_quit' function"""
    mfunctions = [getattr(self, method) for method in dir(self) if method.startswith('menuitem_') and method[9:11].isnumeric() and method[11:12]=='_']
    mfunctions.append(self.menuitem_quit)
    return mfunctions    

########################################################################################

class Prompter(object):
  @classmethod
  def get_input(cls, prompt_text, default_value):
      response = input(f"{prompt_text} [{default_value}]: ")
      if not response:
          # response = None
          response = default_value
      return response

  @classmethod
  def get_multichoice(cls, title, options_list, allow_cancel=False, result_type='value'):
    """Show a list of multichoice options, and return the value selected.  
       The 'options-list' is a list where each item is one of the following:
        - [value, description]
        - [value]                = equivalent to [value, value]
        - value                  = equivalent to [value, value]
       
       'allow_cancel'  param causes menu cancellation to raise a KeyBoardInterrupt - otherwise menu is displayed again
       'result_type'   param determines the desired result type - ie: 'value' / 'description' / 'index'
      
    """
    values       = [option_item[0]       if type(option_item) is list else option_item  for option_item in options_list]
    descriptions = [option_item[0:2][-1] if type(option_item) is list else option_item  for option_item in options_list]

    # show menu and process results
    menu_entry_index = TerminalMenu(descriptions, title=title).show()
    if (menu_entry_index is None) and (not allow_cancel):
      raise KeyboardInterrupt
    value = values[menu_entry_index]
    description = descriptions[menu_entry_index]

    print(f'{title} {value}')

    # return value/description/index
    assert result_type in ('value', 'description', 'index')
    if result_type == 'value':
      return value
    if result_type == 'description':
      return description
    if result_type == 'index':
      return menu_entry_index

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


