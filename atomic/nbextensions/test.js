/*"""
==================
test.js
==================
Test visualization application for the universe container (atomic package).
*/
'use strict';


require.config({
    shim: {
        'nbextensions/exa/apps/app3d': {
            exports: 'App3D'
        },

        'nbextensions/exa/apps/gui': {
            exports: 'ContainerGUI'
        },

        'nbextensions/exa/atomic/ao': {
            exports: 'AO'
        },

        'nbextensions/exa/atomic/gto': {
            exports: 'GTO'
        },
    },
});


define([
    'nbextensions/exa/apps/app3d',
    'nbextensions/exa/apps/gui',
    'nbextensions/exa/atomic/ao',
    'nbextensions/exa/atomic/gto'
], function(App3D, ContainerGUI, AO, GTO) {
    class UniverseTestApp {
        /*"""
        UniverseTestApp
        ==================
        A test application for the universe container (atomic package).
        */
        constructor(view) {
            /*"""
            constructor
            --------------
            Args:
                view: Backbone.js view (DOMWidgetView container representation)
            */
            console.log('here11');
            this.view = view;
            this.view.create_canvas();
            this.axis = [];
            this.active_objs = [];
            this.dimensions = {
                'xmin': -24.0,
                'xmax': 24.0,
                'ymin': -24.0,
                'ymax': 24.0,
                'zmin': -24.0,
                'zmax': 24.0,
                'dx': 2.0,
                'dy': 2.0,
                'dz': 2.0
            };
            this.field = new AO(this.dimensions, '1s');
            this.app3d = new App3D(this.view.canvas);
            this.create_gui();
            this.axis = this.app3d.add_unit_axis();
            this.render_ao();
            this.ao.folder.open();
            this.app3d.set_camera({x: 5.5, y: 5.5, z: 5.5});
            this.view.container.append(this.gui.domElement);
            this.view.container.append(this.gui.custom_css);
            this.view.container.append(this.view.canvas);
            var view_self = this.view;
            this.view.on('displayed', function() {
                view_self.app.app3d.animate();
                view_self.app.app3d.controls.handleResize();
            });
        };

        create_gui() {
            /*"""
            create_gui
            --------------
            Creates the standard style container gui instance and populates
            with relevant controls for this application.
            */
            var self = this;
            self.return = false;
            this.gui = new ContainerGUI(this.view.gui_width);

            this.top = {
                'demo': 'Hydrogen Wave Functions',
                'demos': ['Hydrogen Wave Functions', 'Gaussian Type Orbitals', 'Cube', 'Trajectory'],
                'play': function() {
                    console.log('pushed play');
                },
                'fps': 24,
                'save field': function() {
                    var field = {
                        'ox': self.field.xmin, 'oy': self.field.ymin, 'oz': self.field.zmin,
                        'xi': self.field.dx, 'yj': self.field.dy, 'zk': self.field.dz,
                        'nx': self.field.nx, 'ny': self.field.ny, 'nz': self.field.nz,
                        'values': JSON.stringify(self.field.values),
                        'label': self.field.function
                    }
                    self.view.send({'type': 'field', 'data': field});
                }
            };
            this.top['demo_dropdown'] = this.gui.add(this.top, 'demo', this.top['demos']);
            this.top['play_button'] = this.gui.add(this.top, 'play');
            this.top['send_button'] = this.gui.add(this.top, 'save field');
            this.top['fps_slider'] = this.gui.add(this.top, 'fps', 1, 60);
            this.ao = {
                'function': '1s',
                'functions': ['1s', '2s', '2px', '2py', '2pz',
                              '3s', '3px', '3py', '3pz',
                              '3dz2', '3dxz', '3dyz', '3dx2-y2', '3dxy'],
                'isovalue': 0.005
            };
            this.ao['folder'] = this.gui.addFolder('Hydrogen Wave Functions');
            this.ao['func_dropdown'] = this.ao.folder.add(this.ao, 'function', this.ao['functions']);
            this.ao['isovalue_slider'] = this.ao.folder.add(this.ao, 'isovalue', 0.0, 0.4);

            this.ao['isovalue_slider'].onFinishChange(function(value) {
                self.ao['isovalue'] = value;
                self.render_ao();
            });

            this.ao['func_dropdown'].onFinishChange(function(value) {
                self.ao['function'] = value;
                self.render_ao();
            });

            this.gto = {
                'function': '1s',
                'functions': ['1s', '2s', '2px', '2py', '2pz',
                              '3s', '3px', '3py', '3pz',
                              '3dz2', '3dxz', '3dyz', '3dx2-y2', '3dxy'],
                'isovalue': 0.01
            };

            this.gto['folder'] = this.gui.addFolder('Gaussian Type Orbitals');
            this.gto['func_dropdown'] = this.gto.folder.add(this.gto, 'function', this.gto['functions']);
            this.gto['isovalue_slider'] = this.gto.folder.add(this.gto, 'isovalue', 0.0, 0.4);

            this.gto['isovalue_slider'].onFinishChange(function(value) {
                self.gto['isovalue'] = value;
                self.render_gto();
            });

            this.gto['func_dropdown'].onFinishChange(function(value) {
                self.gto['function'] = value;
                self.render_gto();
            });
        };

        render_ao() {
            this.field = new AO(this.dimensions, this.ao['function']);
            console.log('inside render AO');
            console.log(this.field);
            this.app3d.remove_meshes(this.active_objs);
            this.active_objs = this.app3d.add_scalar_field(this.field, this.ao['isovalue'], 2);
        };

        render_gto() {
            this.field = new GTO(this.dimensions, this.gto['function']);
            this.app3d.remove_meshes(this.active_objs);
            this.active_objs = this.app3d.add_scalar_field(this.field, this.gto['isovalue'], 2);
        };

        resize() {
            this.app3d.resize();
        };
    };


    return UniverseTestApp;
});
