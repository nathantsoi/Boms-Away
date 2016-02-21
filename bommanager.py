#!/usr/bin/env python

import os
import sch
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty,\
    ObjectProperty, ListProperty, DictProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.factory import Factory
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.adapters.listadapter import ListAdapter
from kivy.garden.NavigationDrawer import NavigationDrawer
from kivy.core.window import Window
import csv

# TODO: Normalize all input schematic components to follow field
# guidelines

SidePanel_AppMenu = {'Load Schematic': ['on_load', None],
                     'Save Schematic': ['on_save', None],
                     'Components': ['on_component', None],
                     'Component Types': ['on_type', None],
                     'Export BOM as CSV': ['on_export_csv', None],
                     'Quit': ['on_quit', None],
                     }
id_AppMenu_METHOD = 0
id_AppMenu_PANEL = 1


class SidePanel(BoxLayout):
    pass


class NavDrawer(NavigationDrawer):
    def __init__(self, **kwargs):
        super(NavDrawer, self).__init__(**kwargs)

    def close_sidepanel(self, animate=True):
        if self.state == 'open':
            if animate:
                self.anim_to_state('closed')
            else:
                self.state = 'closed'


class MenuItem(Button):
    def __init__(self, **kwargs):
        super(MenuItem, self).__init__(**kwargs)
        self.bind(on_press=self.menuitem_selected)

    def menuitem_selected(self, *args):
        print ("{} {} {}".format(
            self.text,
            SidePanel_AppMenu[self.text],
            SidePanel_AppMenu[self.text][id_AppMenu_METHOD]
        ))
        try:
            function_to_call = SidePanel_AppMenu[self.text][id_AppMenu_METHOD]
        except:
            print 'errore di configurazione dizionario voci menu'
            return
        getattr(AppRoot, function_to_call)()


class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class ExportDialog(FloatLayout):
    export = ObjectProperty(None)
    cancel = ObjectProperty(None)

# TODO: Attempt to fold selectablelist/componentview/componenttypeview
# into one base class, then subclass for the editor views
class SelectableList(BoxLayout):
    component_view = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(SelectableList, self).__init__(**kwargs)


# TODO: Enumerate field values
class ComponentWrapper(object):
    def __init__(self, base_component):
        self._cmp = base_component

    def _get_field(self, field_no):
        return (
            [x for x in self._cmp.fields if x['id'] == str(field_no)][0]
        )

    def _set_field_value(self, field_no, value):
        f = self._get_field(field_no)
        f['ref'] = '"{}"'.format(value)

    def _get_field_value(self, field_no):
        try:
            return self._get_field(field_no)['ref'].strip('"')
        except:
            return ''

    @property
    def reference(self):
        return self._get_field_value(0)

    @property
    def value(self):
        return self._get_field_value(1)

    @property
    def footprint(self):
        return self._get_field_value(2)

    @property
    def is_virtual(self):
        if self._cmp.labels['ref'][0] == '#':
            return True
        return False

    @property
    def manufacturer(self):
        return self._get_field_value(7)

    @manufacturer.setter
    def manufacturer(self, mfr):
        self._set_field_value(7, mfr)

    @property
    def supplier(self):
        return self._get_field_value(6)

    @supplier.setter
    def supplier(self, sup):
        self._set_field_value(6, sup)

    @property
    def manufacturer_pn(self):
        return self._get_field_value(5)

    @manufacturer_pn.setter
    def manufacturer_pn(self, pn):
        self._set_field_value(5, pn)

    @property
    def supplier_pn(self):
        return self._get_field_value(4)

    @supplier_pn.setter
    def supplier_pn(self, pn):
        self._set_field_value(4, pn)

    def __str__(self):
        return '\n'.join([
            '\nComponent: {}'.format(self.reference),
            '-' * 20,
            'Value: {}'.format(self.value),
            'Footprint: {}'.format(self.footprint),            
        ])

class ComponentTypeContainer(object):
    def __init__(self):
        self._components = []

    def add(self, component):
        # Only allow insertion of like components
        if len(self._components):
            if ((component.value != self._components[0].value) or
                (component.footprint != self._components[0].footprint)):
                raise Exception("Attempted to insert unlike component into ComponentTypeContainer")

        self._components.append(component)

    def __len__(self):
        return len(self._components)

    # TODO: Add validation function and enforce!

    @property
    def refs(self):
        return ';'.join([x.reference for x in self._components])

    @property
    def value(self):
        return self._components[0].value

    @property
    def footprint(self):
        return self._components[0].footprint

    @property
    def manufacturer(self):
        return self._components[0].manufacturer

    @property
    def manufacturer_pn(self):
        return self._components[0].manufacturer_pn

    @property
    def supplier(self):
        return self._components[0].supplier

    @property
    def supplier_pn(self):
        return self._components[0].supplier_pn


class ComponentView(BoxLayout):
    top_box = ObjectProperty(None)
    scrollbox = ObjectProperty(None)
    comp_list = ObjectProperty(None)
    data = ListProperty([])

    component_map = DictProperty({})
    component_type_map = DictProperty({})
    schematics = DictProperty({})

    def __init__(self, **kwargs):
        super(ComponentView, self).__init__(**kwargs)

    def attach_data(self, data):
        self.comp_list.component_view.adapter.data = data

    def attach_selection_callback(self, cb):
        self.comp_list.component_view.adapter.bind(on_selection_change=cb)

class ComponentTypeView(BoxLayout):
    top_box = ObjectProperty(None)
    scrollbox = ObjectProperty(None)
    comp_type_list = ObjectProperty(None)
    data = ListProperty([])

    component_map = DictProperty({})
    component_type_map = DictProperty({})
    schematics = DictProperty({})

    def __init__(self, **kwargs):
        super(ComponentTypeView, self).__init__(**kwargs)

    def attach_data(self, data):
        self.comp_type_list.component_view.adapter.data = data

    def attach_selection_callback(self, cb):
        self.comp_type_list.component_view.adapter.bind(on_selection_change=cb)

class BomManagerApp(App):
    top_box = ObjectProperty(None)
    scrollbox = ObjectProperty(None)
    comp_list = ObjectProperty(None)
    component_data = ListProperty([])
    component_type_data = ListProperty([])

    component_map = DictProperty({})
    component_type_map = DictProperty({})
    schematics = DictProperty({})

    def print_component_type(self, adapter, *args):
        # TODO: Make component types a map of maps (instead of a map
        # of lists)
        long_key = adapter.selection.pop().text
        val, fp = [x.strip() for x in long_key.split('|')]
        type_key = '{}|{}'.format(val, fp)
        print self.component_type_map[type_key]

    def print_selected_component(self, adapter, *args):
        long_key = adapter.selection.pop().text
        ref, val, fp = [x.strip() for x in long_key.split('|')]
        type_key = '{}|{}'.format(val, fp)
        print self.component_map[ref]

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)

        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def show_export(self):
        content = ExportDialog(export=self.export_csv, cancel=self.dismiss_popup)
        self._popup = Popup(title="Export BOM CSV", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def export_csv(self, path, filename):

        # TODO: Check if file exists and ask about overwrite
        with open(os.path.join(path, filename), 'w') as csvfile:
            wrt = csv.writer(csvfile)

            wrt.writerow(['Refs', 'Value', 'Footprint', 'QTY', 'MFR', 'MPN', 'SPR', 'SPN'])

            for ctype in sorted(self.component_type_map):
                ctcont = self.component_type_map[ctype]
                wrt.writerow([
                    ctcont.refs,
                    ctcont.value,
                    ctcont.footprint,
                    len(ctcont),
                    ctcont.manufacturer,
                    ctcont.manufacturer_pn,
                    ctcont.supplier,
                    ctcont.supplier_pn,
                ])

        self.dismiss_popup()

    def _walk_sheets(self, base_dir, sheets):
        for sheet in sheets:
            sheet_name = sheet.fields[0]['value'].strip('"')
            sheet_sch = sheet.fields[1]['value'].strip('"')
            schematic = sch.Schematic(os.path.join(base_dir, sheet_sch))
            self.schematics[sheet_name] = (
                sch.Schematic(os.path.join(base_dir, sheet_sch))
            )
            self._walk_sheets(base_dir, schematic.sheets)

    def _reset(self):
        self.schematics = {}
        self.component_data = []
        self.component_type_data = []
        self.component_map = {}
        self.component_type_map = {}

    def load(self, path, filename):
        self.dismiss_popup()

        # Enable the save button if we have a live schematic
        self.side_panel.save_button.disabled = False
        self.side_panel.export_button.disabled = False

        # remove old schematic information
        self._reset()

        base_dir = path
        top_sch = os.path.split(filename[0])[-1]
        top_name = os.path.splitext(top_sch)[0]

        compmap = {}

        self.schematics[top_name] = (
            sch.Schematic(os.path.join(base_dir, top_sch))
        )

        # Recursively walks sheets to locate nested subschematics
        self._walk_sheets(base_dir, self.schematics[top_name].sheets)

        component_data = []
        type_data = []
        for name, schematic in self.schematics.items():
            for _cbase in schematic.components:
                c = ComponentWrapper(_cbase)

                # Skip virtual components (power, gnd, etc)
                if c.is_virtual:
                    continue

                comp_type_key = '{}|{}'.format(c.value, c.footprint)
                comp_key = c.reference

                self.component_map[comp_key] = c

                if comp_type_key not in self.component_type_map:
                    self.component_type_map[comp_type_key] = ComponentTypeContainer()
                self.component_type_map[comp_type_key].add(c)

                component_data.append('{} | {} | {}'.format(c.reference,
                                                            c.value,
                                                            c.footprint))
                type_data.append('{} | {}'.format(c.value, c.footprint))

        # Uniquify and sort data
        self.component_type_data = sorted(list(set(type_data)))
        self.component_data = sorted(list(set(component_data)))

        self.comp_view.attach_selection_callback(self.print_selected_component)
        self.comp_view.attach_data(self.component_data)

        self.type_view.attach_selection_callback(self.print_component_type)
        self.type_view.attach_data(self.component_type_data)


    def build(self):
        global AppRoot
        AppRoot = self

        self.navdrawer = NavDrawer()

        self.side_panel = SidePanel()
        self.navdrawer.add_widget(self.side_panel)

        self.comp_view = ComponentView()
        self.type_view = ComponentTypeView()

        self.main_panel = self.comp_view

        self.navdrawer.anim_type = 'slide_above_anim'
        self.navdrawer.add_widget(self.main_panel)
        Window.bind(mouse_pos=self.on_motion)

        return self.navdrawer

    def on_motion(self, etype, motionevent):
        if self.navdrawer.state == 'closed':
            if motionevent[0] < 50:
                self.navdrawer.toggle_state()
        else:
            # TODO: Fix this calculation, it isn't correct
            if motionevent[0] > self.navdrawer.side_panel_width / 2:
                self.navdrawer.close_sidepanel()

    def on_load(self):
        """
        Recursively loads a KiCad schematic and all subsheets
        """
        self.navdrawer.close_sidepanel()
        self.show_load()

    def on_component(self):
        """
        Switches to component (individual) view
        """
        self._switch_main_page(self.comp_view)

    def on_save(self):
        """
        Saves all schematics
        """
        for name, schematic in self.schematics.items():
            schematic.save()

    def on_type(self):
        """
        Switches to component type (grouped) view
        """
        self._switch_main_page(self.type_view)

    def on_quit(self):
        """
        Quits the application
        """
        exit(0)

    def on_export_csv(self):
        """
        Exports Bill of Materials as a CSV File
        """
        self.show_export()

    def _switch_main_page(self, panel):
        self.navdrawer.close_sidepanel()
        self.navdrawer.remove_widget(self.main_panel)
        self.navdrawer.add_widget(panel)
        self.main_panel = panel


if __name__ == '__main__':

    BomManagerApp().run()
