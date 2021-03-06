# imports
from gi.repository import Gtk, GObject, GLib
from labsight.motor import Motor
from labsight import controller
from control.dialogs import NewMotorDialog
import control.config as config
import os
from threading import Thread
import queue

# Motor List Class
class MotorList(Gtk.Box):

    # stack
    stack = None

    # widgets
    list_box = None

    scrolled_window = None

    motors = {}

    serial_worker = None
    serial_queue = None

    # setup signals
    __gsignals__ = {
        "done-loading": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
        "control-motor": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))
    }

    # constructor
    def __init__(self):
        # initiate grid
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        content.props.expand = True
        content.get_style_context().add_class("motor-list")

        # create spinner
        grid = Gtk.Grid()
        grid.props.expand = True
        grid.props.halign = Gtk.Align.CENTER
        grid.props.valign = Gtk.Align.CENTER
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        grid.attach(self.spinner, 0, 0, 1, 1)
        label = Gtk.Label("Scanning Ports for Connected Motors")
        label.get_style_context().add_class("new-motor-title")
        grid.attach(label, 0, 1, 1, 1)
        # self.stack.add_named(grid, "loading")

        # create list box
        self.create_list_box()
        content.add(self.list_box)

        loading_box = Gtk.Box()
        loading_box.props.margin = 6
        loading_box.get_style_context().add_class("card")

        self.create_loading_stack()
        loading_box.add(self.loading_stack)
        content.add(loading_box)

        # add to scrolled window
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.add(content)

        # add to this
        self.add(self.scrolled_window)

        self.show_all()

    def create_list_box(self):
        self.list_box = Gtk.ListBox()
        # self.list_box.props.expand = False
        self.list_box.props.selection_mode = Gtk.SelectionMode.NONE

        self.list_box.get_style_context().add_class("motor-list")

    def create_loading_stack(self):
        self.loading_stack = Gtk.Stack()
        self.loading_stack.props.margin = 6

        self.refresh_button = Gtk.Button().new_with_label("Reload")
        self.refresh_button.props.hexpand = False

        self.delete_button = Gtk.Button().new_with_label("Delete")
        self.delete_button.props.hexpand = False
        self.delete_button.props.no_show_all = True
        self.delete_button.show()

        self.cancel_button = Gtk.Button().new_with_label("Cancel")
        self.cancel_button.props.hexpand = False
        self.cancel_button.props.no_show_all = True
        self.cancel_button.hide()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.props.halign = Gtk.Align.CENTER
        box.add(self.refresh_button)
        box.add(self.delete_button)
        box.add(self.cancel_button)

        self.loading_stack.add_named(box, "refresh")

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.props.hexpand = True
        self.progress_bar.props.show_text = True
        self.progress_bar.props.text = "Scanning Ports for Attached Motors"

        def pulse():
            self.progress_bar.pulse()
            return True
        GLib.timeout_add(250, pulse)

        self.loading_stack.add_named(self.progress_bar, "progress")

        def delete(origin=None, props=None):
            for mid in self.motors:
                self.motors[mid].show_delete()
                self.delete_button.hide()
                self.cancel_button.show()
        self.delete_button.connect("clicked", delete)

        def cancel(origin=None, props=None):
            for mid in self.motors:
                self.motors[mid].hide_delete()
                self.delete_button.show()
                self.cancel_button.hide()
        self.cancel_button.connect("clicked", cancel)

        # connect refresh button signal
        def clicked(origin=None, props=None):
            cancel()
            self.start_load()
        self.refresh_button.connect("clicked", clicked)

    def load_from_files(self):
        file_list = os.listdir(config.MOTOR_CONFIG_DIR)
        for f in file_list:
            (mid, ext) = f.split(".")
            if ext == "yml" or ext == "yaml":
                if mid not in self.motors:
                    m = Motor(config.MOTOR_CONFIG_DIR, None, mid)

                    motor_list_child = MotorListChild(m)
                    def f(motor):
                        self.emit("control-motor", motor)
                    motor_list_child.control_callback = f

                    def d(origin=None, props=None):
                        motor_list_child.destroy()
                        del self.motors[mid]
                        self.queue_draw()
                    motor_list_child.delete_callback = d

                    self.motors[mid] = motor_list_child
                    self.list_box.insert(motor_list_child, -1)

    def start_load(self):

        self.loading_stack.set_visible_child_name("progress")

        self.load_from_files()

        if self.serial_worker != None:
            # print("waiting for serial worker to end")
            self.serial_worker.join()

        self.serial_queue = queue.Queue()
        self.serial_worker = SerialWorker(self.serial_queue, self.end_load)
        self.serial_worker.start()

        while self.serial_queue != None:

            if not self.serial_queue.empty():
                task = self.serial_queue.get()
                task()

            while Gtk.events_pending():
                Gtk.main_iteration()

    def end_load(self, result):

        # loop through our created motor objects
        for mid in self.motors:
            # check to see if their id is in the result, if so, connect their serial otherwise disconnect it
            if mid in result:
                self.motors[mid].connect_serial(result[mid])
                del result[mid]
            else:
                self.motors[mid].disconnect_serial()

        # if we still have results left, load from files and rerun this method
        if len(result) > 0:
            self.load_from_files()
            self.end_load(result)

        self.loading_stack.set_visible_child_name("refresh")

        self.serial_queue = None
        self.emit("done-loading")

        self.queue_draw()

class SerialWorker(Thread):
    # construct self
    def __init__(self, ser_queue, callback):
        Thread.__init__(self)

        self.callback = callback
        self.queue = ser_queue

    def run(self):
        serials = controller.getAttachedSerials(config.MOTOR_CONFIG_DIR)

        # self.callback(serials)
        self.queue.put(lambda: self.callback(serials))

class MotorListChild(Gtk.ListBoxRow):

    # grid for this
    grid = None

    # motor id
    motor = None

    # widgets
    motor_detected_label = None

    # status 0 = disconnected, 1 = connecting, 2 = connected
    status = 0

    # constructor
    def __init__(self, motor):
        Gtk.ListBoxRow.__init__(self)

        # make motor available throughout the class
        self.motor = motor

        # set motor properties
        if not self.motor.hasProperty("configured"):
            self.motor.setProperty("configured", False)

        # if motor is not already configured, make sure all of our properties exist
        if self.motor.getProperty("configured") == False:
            self.motor.setProperty("display-name", "Motor")
            self.motor.setProperty("axis", None)
            self.motor.setProperty("type", None)
            self.motor.setProperty("calibrated", False)
            self.motor.setProperty("calibrated-steps", -1)
            self.motor.setProperty("calibrated-units", -1)

        self.control_callback = None
        self.delete_callback = None

        # build ui
        self.update_ui()

    def clean_ui(self):
        for child in self.get_children():
            child.destroy()

    def update_ui(self):
        # add class to self
        self.get_style_context().add_class("card")
        self.props.margin = 6

        # box
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # create info grid
        info_grid = Gtk.Grid()
        info_grid.props.expand = True
        info_grid.props.halign = Gtk.Align.START
        info_grid.props.valign = Gtk.Align.CENTER
        info_grid.props.column_spacing = 6
        info_grid.props.row_spacing = 3

        # create button grid
        button_grid = Gtk.Grid()
        button_grid.props.expand = True
        button_grid.props.halign = Gtk.Align.END
        button_grid.props.valign = Gtk.Align.CENTER
        button_grid.props.column_spacing = 6
        button_grid.props.row_spacing = 6

        # clean ui
        self.clean_ui()

        # universal widgets
        self.control_button = Gtk.Button().new_with_label("Control")
        self.control_button.connect("clicked", self.control)

        self.connect_button = Gtk.Button().new_with_label("Connect")
        self.connect_button.connect("clicked", self.connect)

        self.delete_button = Gtk.Button().new_with_label("Delete")
        self.delete_button.get_style_context().add_class("destructive-action")
        self.delete_button.connect("clicked", self.delete)
        self.delete_button.props.no_show_all = True
        self.delete_button.hide()

        self.configure_button = Gtk.Button().new_with_label("Configure")
        self.configure_button.connect("clicked", self.configure)

        self.status_label = Gtk.Label("")
        self.status_label.props.use_markup = True
        self.status_label.props.halign = Gtk.Align.START

        if self.motor.getProperty("configured") == True:
            # info labels
            display_label = Gtk.Label(self.motor.getProperty("display-name"))
            display_label.props.wrap = True
            display_label.props.halign = Gtk.Align.START
            display_label.get_style_context().add_class("motor-detected")

            axis_label = Gtk.Label("<b>Axis:</b> {}".format(self.motor.getProperty("axis")))
            axis_label.props.use_markup = True
            axis_label.props.halign = Gtk.Align.START

            type_label = Gtk.Label("<b>Type:</b> {}".format(self.motor.getProperty("type")))
            type_label.props.use_markup = True
            type_label.props.halign = Gtk.Align.START

            id_label = Gtk.Label("<b>ID:</b> {}".format(self.motor.getProperty("id")))
            id_label.props.use_markup = True
            id_label.props.halign = Gtk.Align.START

            # attach things to the grid
            info_grid.attach(display_label, 0, 0, 1, 1)
            info_grid.attach(axis_label, 0, 1, 1, 1)
            info_grid.attach(type_label, 0, 2, 1, 1)
            info_grid.attach(self.status_label, 1, 1, 1, 1)
            info_grid.attach(id_label, 1, 2, 1, 1)

            button_grid.attach(self.control_button, 0, 0, 1, 1)
            button_grid.attach(self.connect_button, 0, 1, 1, 1)
            button_grid.attach(self.configure_button, 0, 2, 1, 1)
            button_grid.attach(self.delete_button, 0, 3, 1, 1)

            # if there is no serial, add disconnected class
            if self.motor.serial == None:
                self.get_style_context().add_class("insensitive")
            else:
                self.get_style_context().remove_class("insensitive")

        else:
            # create motor detected
            motor_detected_label = Gtk.Label("New Motor Detected")
            motor_detected_label.props.wrap = True
            motor_detected_label.props.expand = True
            motor_detected_label.get_style_context().add_class("motor-detected")

            motor_id = Gtk.Label("<b>ID:</b> {}".format(self.motor.getProperty("id")))
            motor_id.props.use_markup = True
            motor_id.props.halign = Gtk.Align.START
            motor_id.props.wrap = True

            # attach things to the grid
            info_grid.attach(motor_detected_label, 0, 0, 1, 1)
            info_grid.attach(motor_id, 0, 1, 1, 1)

            button_grid.attach(self.configure_button, 0, 0, 1, 1)

        # add grids to box
        box.add(info_grid)
        box.add(button_grid)

        # add resulting grid to self
        self.add(box)

        # show all
        self.show_all()

        if self.motor.serial == None:
            self.control_button.props.visible = False
            self.connect_button.props.visible = True
            self.status = 0
        else:
            self.control_button.props.visible = True
            self.connect_button.props.visible = False
            self.status = 2

        self.update_status()

    def show_delete(self):
        self.control_button.hide()
        self.connect_button.hide()
        self.delete_button.show()
        self.configure_button.hide()

    def hide_delete(self):
        self.update_ui()

    def control(self, event, param=None):
        self.control_callback(self.motor)

    def connect(self, event, param=None):
        print("connect all the things")

    def configure(self, event, param=None):
        if self.motor.getProperty("configured") == True:
            dialog = NewMotorDialog(dname=self.motor.getProperty("display-name"),
                                    axis=self.motor.getProperty("axis"),
                                    mtype=self.motor.getProperty("type"))
        else:
            dialog = NewMotorDialog()

        # define method for applying changes from dialog
        def apply_configurations(event, param=None):
            # save configurations
            self.motor.setProperty("configured", True)
            self.motor.setProperty("display-name", dialog.display_name)
            self.motor.setProperty("axis", dialog.axis_name)
            self.motor.setProperty("type", dialog.type_name)

            # destroy dialog
            dialog.destroy()

            # update self
            self.update_ui()

        # connect to applied signal
        dialog.connect("applied", apply_configurations)

        # start the dialog
        dialog.run()

    def delete(self, origin=None, param=None):
        self.motor.remove()
        if self.delete_callback != None:
            self.delete_callback()

    def update_status(self):
        if self.status == 0:
            self.status_label.props.label = "<b>Status:</b> {}".format("Disconnected")

        elif self.status == 1:
            self.status_label.props.label = "<b>Status:</b> {}".format("Connecting…")

        elif self.status == 2:
            self.status_label.props.label = "<b>Status:</b> {}".format("Connected")

    def connect_serial(self, serial):
        self.motor.serial = serial
        self.update_ui()

    def disconnect_serial(self):
        if self.motor.serial != None:
            self.motor.serial.close()

        self.motor.serial = None
        self.update_ui()
