
# imports
from gi.repository import Gtk, GObject, Gio
import control.config as config
from control.views.WelcomeView import WelcomeView
from control.views.MotorList import MotorList
from control.views.MotorControl import MotorControl

# window class
class MainWindow(Gtk.Window):

    """ properties and widgets """
    stack = None

    # views
    welcome = None

    # constructor
    def __init__(self, app):
        Gtk.Window.__init__(self, title=config.APP_TITLE)

        # window settings
        self.set_size_request(650, 700)

        # build ui
        self.build_ui()

        # connect signals
        self.connect_signals()

        # show all the things
        self.show_all()

        # refresh motors
        self.refresh(None)

    def build_ui(self):
        # initiate stack
        self.stack = Gtk.Stack()

        # create welcome view and add it to the stack
        self.welcome = WelcomeView()
        self.stack.add_named(self.welcome, "welcome")

        self.motor_list = MotorList()
        self.stack.add_named(self.motor_list, "motor-list")

        self.motor_control = MotorControl()
        self.stack.add_named(self.motor_control, "motor-control")

        self.add(self.stack)

    def connect_signals(self):
        self.connect("delete-event", self.destroy) # connect the close button to destroying the window
        self.welcome.connect("refresh-motor-list", self.refresh)
        self.motor_list.connect("done-loading", self.done_loading)
        self.motor_list.connect("control-motor", self.control_motor)

    # signal functions
    def destroy(self, event, param=None):
        Gtk.main_quit() 

    def refresh(self, event, param=None):
        self.stack.set_visible_child_name("motor-list")
        self.motor_list.start_load()

    def done_loading(self, event, param=None):
        if len(self.motor_list.list_box.get_children()) < 1:
            self.stack.set_visible_child_name("welcome")

    def control_motor(self, event, motor):
        self.stack.set_visible_child_name("motor-control")