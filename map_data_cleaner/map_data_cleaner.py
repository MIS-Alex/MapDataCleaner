# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapDataCleaner
                                 A QGIS plugin
 This plugin downloads and cleans data for mapping.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-01-09
        git sha              : $Format:%H$
        copyright            : (C) 2020 by McKenzie Intelligence
        email                : dev@mckenzieintelligence.co.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from qgis.core import QgsProject, QgsMessageLog, QgsVectorLayer, Qgis
from qgis import processing

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .map_data_cleaner_dialog import MapDataCleanerDialog
import os.path
import requests
import json


class MapDataCleaner:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'MapDataCleaner_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&MapDataCleaner')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MapDataCleaner', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/map_data_cleaner/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Data Cleaner'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&MapDataCleaner'),
                action)
            self.iface.removeToolBarIcon(action)

    def select_output_file(self):
        filename, _filter = QFileDialog.getSaveFileName(
            self.dlg, "Select   output file ", "", '*.geojson')
        self.dlg.OutputFile.setText(filename)

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = MapDataCleanerDialog()
            self.dlg.FileButton.clicked.connect(self.select_output_file)

        self.dlg.DataSelection.clear()
        self.dlg.DataSelection.addItems(['New South Wales: Burn Scar'])

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            filename = self.dlg.OutputFile.text()
            if self.dlg.DataSelection.currentText() == 'New South Wales: Burn Scar':
                incidents = requests.get('http://www.rfs.nsw.gov.au/feeds/majorIncidents.json').json()
                output_dict = {'type': 'FeatureCollection', 'features': []}

                for top_key in incidents:
                    if top_key == 'features':
                        for feature in incidents[top_key]:
                            if feature['geometry']['type'] == 'GeometryCollection':
                                geometry_collections = feature['geometry']['geometries'][1]
                                for polygon in geometry_collections['geometries']:
                                    geometry_dict = {'type': 'Polygon', 'coordinates': polygon['coordinates']}
                                    child_dict = {'type': 'Feature', 'geometry': geometry_dict,
                                                  'properties': feature['properties']}
                                    output_dict['features'].append(child_dict)

                with open(filename, 'w') as output:
                    output.write(json.dumps(output_dict))

                file_path_list = filename.split('/')
                file_name_list = file_path_list[-1].split('.')
                output_layer = QgsVectorLayer(filename, file_name_list[0] + '_raw', 'ogr')
                if int(Qgis.QGIS_VERSION.split('.')[1]) > 4:
                    fixed_geom_lyr = processing.run('qgis:fixgeometries', {'INPUT': output_layer, 'OUTPUT': 'memory:'})
                    QgsProject.instance().addMapLayer(fixed_geom_lyr['OUTPUT'])
                else:
                    from qgis.core import QgsApplication
                    fixed_geom_lyr = QgsApplication.processing.runalg('qgis:fixgeometries', {'INPUT': output_layer, 'OUTPUT': 'memory:'})
                    QgsProject.instance().addMapLayer(fixed_geom_lyr['OUTPUT'])
            pass
