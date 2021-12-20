
from simple_term_menu import TerminalMenu

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
