
from simple_term_menu import TerminalMenu
import inspect

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

