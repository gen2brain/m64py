# -*- coding: utf-8 -*-
# Author: Milan Nikolic <gen2brain@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from m64py.core.defs import *
from m64py.utils import format_tooltip
from m64py.frontend.joystick import Joystick
from m64py.frontend.keymap import SDL_KEYMAP, QT_MODIFIERS, QT_KEYSTRING
from m64py.ui.input_ui import Ui_InputDialog

KEY_RE = re.compile("([a-z]+)\((.*)\)")
AXIS_RE = re.compile("([a-z]+)\((.*?),(.*?)\)")

class Input(QDialog, Ui_InputDialog):

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.parent = parent
        self.config = None
        self.controller = 1
        self.is_joystick = False
        self.set_section("Input-SDL-Control%d" % self.controller)
        self.joystick = Joystick()
        self.add_items()
        self.connect_signals()

    def closeEvent(self, event):
        self.save_config()
        self.close()

    def connect_signals(self):
        self.comboDevice.currentIndexChanged.connect(
                self.on_device_changed)
        self.comboController.currentIndexChanged.connect(
                self.on_controller_changed)

    def show_dialog(self):
        self.config = self.parent.worker.m64p.config
        self.config.open_section(self.section)
        self.device = self.config.get_parameter("device")
        self.is_joystick = bool(self.device >= 0)
        self.get_opts(), self.get_keys()
        self.set_opts(), self.set_keys()
        self.show()

    def set_section(self, section):
        self.section = section

    def add_items(self):
        for controller in range(1, 5):
            self.comboController.addItem(
                    "Controller %s" % controller, controller)

        for plugin, ptype in [("None", 1), ("Mem pak", 2), ("Rumble pak", 5)]:
            self.comboPlugin.addItem(plugin, ptype)

        for mode, mtype in [("Fully Manual", 0),
                ("Auto with named SDL device", 1), ("Fully Automatic", 2)]:
            self.comboMode.addItem(mode, mtype)

        devices = [("Keyboard/Mouse", -1)]
        for num, joy in enumerate(self.joystick.joystick_names):
            devices.append(("Joystick %s (%s)" % (num, joy), num))

        for device, dtype in devices:
            self.comboDevice.addItem(device, dtype)

    def save_config(self):
        self.save_opts()
        self.save_keys()
        self.config.save_file()

    def on_device_changed(self, index):
        self.device = self.comboDevice.itemData(self.comboDevice.currentIndex())
        self.is_joystick = bool(self.device >= 0)

    def on_controller_changed(self, index):
        self.save_config()
        self.controller = self.comboController.itemData(index)
        self.set_section("Input-SDL-Control%d" % self.controller)
        self.config.open_section(self.section)

        self.is_joystick = bool(self.config.get_parameter("device") >= 0)
        if not self.config.parameters[self.section]:
            self.set_default()
        self.get_opts(), self.get_keys()
        self.set_opts(), self.set_keys()

    def set_default(self):
        for key in self.keys.keys():
            if key.startswith("X Axis") or key.startswith("Y Axis"):
                continue
            self.config.set_default(M64TYPE_STRING, key, "", "")
        self.config.set_default(M64TYPE_STRING, "X Axis", "",
                "Analog axis configuration mappings")
        self.config.set_default(M64TYPE_STRING, "Y Axis", "", "")
        for key, val in self.opts.items():
            param, tooltip, widget, ptype = val
            if key == "plugged":
                param = False
            elif key == "plugin":
                param = 1
            elif key == "device":
                param = -2
            self.config.set_default(ptype, key, param, tooltip)
        self.config.list_parameters()

    def get_opts(self):
        self.opts = {
            "plugged": (
                self.config.get_parameter("plugged"),
                self.config.get_parameter_help("plugged"),
                self.checkPlugged, M64TYPE_BOOL),
            "mouse": (
                self.config.get_parameter("mouse"),
                self.config.get_parameter_help("mouse"),
                self.checkMouse, M64TYPE_BOOL),
            "plugin": (
                self.config.get_parameter("plugin"),
                self.config.get_parameter_help("plugin"),
                self.comboPlugin, M64TYPE_INT),
            "device": (
                self.config.get_parameter("device"),
                self.config.get_parameter_help("device"),
                self.comboDevice, M64TYPE_INT),
            "mode": (
                self.config.get_parameter("mode"),
                self.config.get_parameter_help("mode"),
                self.comboMode, M64TYPE_INT),
            "AnalogDeadzone": (
                self.config.get_parameter("AnalogDeadzone"),
                self.config.get_parameter_help("AnalogDeadzone"),
                (self.spinDeadzoneX, self.spinDeadzoneY), M64TYPE_STRING),
            "AnalogPeak": (
                self.config.get_parameter("AnalogPeak"),
                self.config.get_parameter_help("AnalogPeak"),
                (self.spinPeakX, self.spinPeakY), M64TYPE_STRING)
            }

    def set_opts(self):
        for key, val in self.opts.items():
            param, tooltip, widget, ptype = val
            if ptype == M64TYPE_BOOL:
                if param:
                    widget.setChecked(param)
                else:
                    widget.setChecked(False)
            elif ptype == M64TYPE_INT:
                widget.setCurrentIndex(widget.findData(param))
            elif ptype == M64TYPE_STRING:
                if key in ["AnalogDeadzone", "AnalogPeak"]:
                    if param:
                        paramX, paramY = param.split(",")
                        spin1, spin2 = widget
                        spin1.setValue(int(paramX))
                        spin2.setValue(int(paramY))
                        spin1.setToolTip(format_tooltip(tooltip))
                        spin2.setToolTip(format_tooltip(tooltip))
                else:
                    widget.setText(param)
            if key not in ["AnalogDeadzone", "AnalogPeak"] and tooltip:
                widget.setToolTip(tooltip)

    def save_opts(self):
        for key, val in self.opts.items():
            param, tooltip, widget, ptype = val
            if ptype == M64TYPE_BOOL:
                self.config.set_parameter(key,
                        widget.isChecked())
            elif ptype == M64TYPE_INT:
                self.config.set_parameter(key,
                        widget.itemData(widget.currentIndex()))
            elif ptype == M64TYPE_STRING:
                if key in ["AnalogDeadzone", "AnalogPeak"]:
                    spin1, spin2 = widget
                    self.config.set_parameter(key,"%s,%s" % (
                        spin1.value(), spin2.value()))
                else:
                    self.config.set_parameter(key,
                            str(widget.text()))

    def get_keys(self):
        self.keys = {
            "DPad R": (
                self.get_key("DPad R")[0], self.pushDPad_R),
            "DPad L": (
                self.get_key("DPad L")[0], self.pushDPad_L),
            "DPad D": (
                self.get_key("DPad D")[0], self.pushDPad_D),
            "DPad U": (
                self.get_key("DPad U")[0], self.pushDPad_U),
            "Start": (
                self.get_key("Start")[0], self.pushStart),
            "Z Trig": (
                self.get_key("Z Trig")[0], self.pushZ_Trig),
            "B Button": (
                self.get_key("B Button")[0], self.pushB_Button),
            "A Button": (
                self.get_key("A Button")[0], self.pushA_Button),
            "C Button R": (
                self.get_key("C Button R")[0], self.pushC_Button_R),
            "C Button L": (
                self.get_key("C Button L")[0], self.pushC_Button_L),
            "C Button D": (
                self.get_key("C Button D")[0], self.pushC_Button_D),
            "C Button U": (
                self.get_key("C Button U")[0], self.pushC_Button_U),
            "R Trig": (
                self.get_key("R Trig")[0], self.pushR_Trig),
            "L Trig": (
                self.get_key("L Trig")[0], self.pushL_Trig),
            "Mempak switch": (
                self.get_key("Mempak switch")[0], self.pushMempak),
            "Rumblepak switch": (
                self.get_key("Rumblepak switch")[0], self.pushRumblepak),
            "X Axis L": (
                self.get_key("X Axis")[0], self.pushX_Axis_L),
            "X Axis R": (
                self.get_key("X Axis")[1], self.pushX_Axis_R),
            "Y Axis U": (
                self.get_key("Y Axis")[0], self.pushY_Axis_U),
            "Y Axis D": (
                self.get_key("Y Axis")[1], self.pushY_Axis_D)
            }


    def set_keys(self):
        for key, val in self.keys.items():
            ckey, widget = val
            if key.startswith("X Axis") or key.startswith("Y Axis"):
                self.set_axis(key, ckey, widget)
            elif not ckey:
                widget.setText("Select...")
            elif self.is_joystick:
                widget.setText(str(ckey))
            else:
                widget.setText(self.get_key_name(ckey))

    def save_keys(self):
        self.save_axis()
        for key, val in self.keys.items():
            ckey, widget = val
            if key.startswith("X Axis") or key.startswith("Y Axis"):
                continue
            else:
                val = KEY_RE.findall(str(widget.text()))
                if val:
                    value = str(widget.text())
                    self.config.set_parameter(key, value)
                else:
                    value = self.get_sdl_key(widget.text())
                    if value:
                        self.config.set_parameter(key, "key(%s)" % value)
                    else:
                        continue

    def get_axis(self, axis):
        param = self.config.get_parameter(axis)
        if param:
            return AXIS_RE.findall(param)

    def set_axis(self, key, ckey, widget):
        if key.startswith("X Axis"):
            axis = self.get_axis("X Axis")
            if axis:
                if axis[0][0] == "key":
                    widget.setText(self.get_key_name(ckey))
                else:
                    if "L" in key:
                        widget.setText("%s(%s)" % (axis[0][0], axis[0][1]))
                    elif "R" in key:
                        widget.setText("%s(%s)" % (axis[0][0], axis[0][2]))
            else:
                widget.setText("Select...")
        elif key.startswith("Y Axis"):
            axis = self.get_axis("Y Axis")
            if axis:
                if axis[0][0] == "key":
                    widget.setText(self.get_key_name(ckey))
                else:
                    if "U" in key:
                        widget.setText("%s(%s)" % (axis[0][0], axis[0][1]))
                    elif "D" in key:
                        widget.setText("%s(%s)" % (axis[0][0], axis[0][2]))
            else:
                widget.setText("Select...")

    def save_axis(self):
        xl = KEY_RE.findall(str(self.pushX_Axis_L.text()))
        xr = KEY_RE.findall(str(self.pushX_Axis_R.text()))
        if xl and xr:
            xl, xr = xl[0], xr[0]
            self.config.set_parameter("X Axis", "%s(%s,%s)" % (xl[0],xl[1],xr[1]))
        else:
            xl = self.get_sdl_key(self.pushX_Axis_L.text())
            xr = self.get_sdl_key(self.pushX_Axis_R.text())
            if xl and xr:
                self.config.set_parameter("X Axis", "key(%s,%s)" % (xl,xr))

        yu = KEY_RE.findall(str(self.pushY_Axis_U.text()))
        yd = KEY_RE.findall(str(self.pushY_Axis_D.text()))
        if yu and yd:
            yu, yd = yu[0], yd[0]
            self.config.set_parameter("Y Axis", "%s(%s,%s)" % (yu[0],yu[1],yd[1]))
        else:
            yu = self.get_sdl_key(self.pushY_Axis_U.text())
            yd = self.get_sdl_key(self.pushY_Axis_D.text())
            if yu and yd:
                self.config.set_parameter("Y Axis", "key(%s,%s)" % (yu,yd))

    def get_key(self, key):
        param = self.config.get_parameter(key)
        if not param:
            return [0, 0]

        if not self.is_joystick:
            value = KEY_RE.findall(param)
            items = [item.strip() for item in value[0][1].split(",")]
            if items:
                return items
        else:
            if key.startswith("X Axis"):
                axis = self.get_axis("X Axis")
                return [axis[0][1], axis[0][2]]
            elif key.startswith("Y Axis"):
                axis = self.get_axis("Y Axis")
                return [axis[0][1], axis[0][2]]
            else:
                return [param, 0]
        return [0, 0]

    def get_sdl_key(self, text):
        try:
            if text in QT_KEYSTRING.keys():
                key = QT_KEYSTRING[str(text)]
            else:
                key = QKeySequence(text).__int__()
            return SDL_KEYMAP[key]
        except KeyError:
            return None

    def get_key_name(self, sdl_key):
        if not sdl_key:
            return "Select..."
        try:
            key = Qt.Key_unknown
            for qt, sdl in SDL_KEYMAP.items():
                if sdl == int(sdl_key):
                    key = qt
            if key in QT_MODIFIERS.keys():
                key = QT_MODIFIERS[key]
        except IndexError:
            key = Qt.Key_unknown

        text = QKeySequence(key).toString(QKeySequence.PortableText)
        if key in QT_MODIFIERS.values():
            text = text.replace("+", "")
        return text
