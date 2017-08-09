#//////////////////////////////////////////////////////////////////////////////
#////                                                                       ///
#//// Copyright INRO, 2016-2017.                                            ///
#//// Rights to use and modify are granted to the                           ///
#//// San Diego Association of Governments and partner agencies.            ///
#//// This copyright notice must be preserved.                              ///
#////                                                                       ///
#//// traffic_assignment.py                                                 ///
#////                                                                       ///
#////                                                                       ///
#////                                                                       ///
#////                                                                       ///
#//////////////////////////////////////////////////////////////////////////////

TOOLBOX_ORDER = 20


import inro.modeller as _m
import inro.emme.core.exception as _except
import traceback as _traceback
from contextlib import contextmanager as _context
import numpy
import array
import os


gen_utils = _m.Modeller().module("sandag.utilities.general")
dem_utils = _m.Modeller().module("sandag.utilities.demand")


class TrafficAssignment(_m.Tool(), gen_utils.Snapshot):

    period = _m.Attribute(unicode)
    msa_iteration = _m.Attribute(int)
    relative_gap = _m.Attribute(float)
    max_iterations = _m.Attribute(int)
    num_processors = _m.Attribute(str)
    select_link = _m.Attribute(unicode)
    raise_zero_dist = _m.Attribute(bool)

    tool_run_msg = ""

    def __init__(self):
        self.msa_iteration = 1
        self.relative_gap = 0.0005
        self.max_iterations = 100
        self.num_processors = "MAX-1"
        self.raise_zero_dist = True
        self.attributes = ["period", "msa_iteration", "relative_gap", "max_iterations", 
                           "num_processors", "select_link", "raise_zero_dist"]
        version = os.environ.get("EMMEPATH", "")
        self._version = version[-5:] if version else ""
        self._skim_classes_separately = False  # Used for debugging only
        
    def page(self):
        pb = _m.ToolPageBuilder(self)
        pb.title = "Traffic assignment"
        pb.description = """
Assign traffic demand for the selected time period."""
        pb.branding_text = "- SANDAG - "
        if self.tool_run_msg != "":
            pb.tool_run_status(self.tool_run_msg_status)

        options = [("EA","Early AM"),
                   ("AM","AM peak"),
                   ("MD","Mid-day"), 
                   ("PM","PM peak"),
                   ("EV","Evening")]
        pb.add_select("period", options, title="Period:")
        pb.add_text_box("msa_iteration", title="MSA iteration:", note="If >1 will apply MSA to flows.")

        pb.add_text_box("relative_gap", title="Relative gap:")
        pb.add_text_box("max_iterations", title="Max iterations:")
        dem_utils.add_select_processors("num_processors", pb, self)
        pb.add_text_box("select_link", title="Select link expression:", 
            note="Use any Emme selection expression to identify the link(s) of interest.",
            multi_line=True)
        pb.add_checkbox("raise_zero_dist", title=" ", label="Raise on zero distance value",
            note="Check for and raise an exception if a zero value is found in the SOVGP_DIST matrix.")
        return pb.render()

    def run(self):
        self.tool_run_msg = ""
        try:
            scenario = _m.Modeller().scenario
            results = self(self.period, self.msa_iteration, self.relative_gap, self.max_iterations, 
                           self.num_processors, scenario, self.select_link, self.raise_zero_dist)
            run_msg = "Traffic assignment completed"
            self.tool_run_msg = _m.PageBuilder.format_info(run_msg)
        except Exception as error:
            self.tool_run_msg = _m.PageBuilder.format_exception(
                error, _traceback.format_exc(error))
            raise

    def __call__(self, period, msa_iteration, relative_gap, max_iterations, num_processors, scenario, 
                 select_link=None, raise_zero_dist=True):
        attrs = {
            "period": period, 
            "msa_interation": msa_iteration,
            "relative_gap": relative_gap, 
            "max_iterations": max_iterations, 
            "num_processors": num_processors, 
            "scenario": scenario.id,
            "select_link": select_link,
            "raise_zero_dist": raise_zero_dist,
            "self": str(self)
        }
        self._stats = {}
        with _m.logbook_trace("Traffic assignment for period %s" % period, attributes=attrs):
            gen_utils.log_snapshot("Traffic assignment", str(self), attrs)
            periods = ["EA", "AM", "MD", "PM", "EV"]
            if not period in periods:
                raise _except.ArgumentError(
                    'period: unknown value - specify one of %s' % periods)
            num_processors = dem_utils.parse_num_processors(num_processors)
            classes = [
                {   # 0
                    "name": 'SOVGP', "mode": 's', "PCE": 1, "VOT": 67., "cost": '',
                    "skims": ["GENCOST", "TIME", "DIST"]
                },                      
                {   # 1
                    "name": 'SOVTOLL', "mode": 'S', "PCE": 1, "VOT": 67., "cost": '@cost_auto',      
                    "skims": ["GENCOST", "TIME", "DIST", "MLCOST", "TOLLCOST", "TOLLDIST"]
                },                  
                {   # 2
                    "name": 'HOV2GP', "mode": 's', "PCE": 1, "VOT": 67., "cost": '',                
                    "skims": []  # same as SOV_GP
                },                    
                {   # 3
                    "name": 'HOV2HOV', "mode": 'h', "PCE": 1, "VOT": 67., "cost": '',                
                    "skims": ["GENCOST", "TIME", "DIST", "HOVDIST"]
                },                  
                {   # 4
                    "name": 'HOV2TOLL', "mode": 'H', "PCE": 1, "VOT": 67., "cost": '@cost_hov',      
                    "skims": ["GENCOST", "TIME", "DIST", "MLCOST", "TOLLCOST", "TOLLDIST"]
                },                
                {   # 5 
                    "name": 'HOV3GP', "mode": 's', "PCE": 1, "VOT": 67., "cost": '',                
                    "skims": []  # same as SOV_GP
                },                    
                {   # 6
                    "name": 'HOV3HOV', "mode": 'i', "PCE": 1, "VOT": 67., "cost": '',                
                    "skims": ["GENCOST", "TIME", "DIST", "HOVDIST"]
                },                  
                {   # 7
                    "name": 'HOV3TOLL', "mode": 'I', "PCE": 1, "VOT": 67., "cost": '@cost_hov',      
                    "skims": ["GENCOST", "TIME", "DIST", "MLCOST", "TOLLCOST", "TOLLDIST"]
                },                
                {   # 8
                    "name": 'TRKHGP', "mode": 'v', "PCE": 2.5, "VOT": 89., "cost": '',                
                    "skims": ["GENCOST", "TIME", "DIST"]
                },                    
                {   # 9
                    "name": 'TRKHTOLL',  "mode": 'V', "PCE": 2.5, "VOT": 89., "cost": '@cost_hvy_truck', 
                    "skims": ["GENCOST", "TIME", "DIST", "TOLLCOST"]
                },                
                {   # 10
                    "name": 'TRKLGP',    "mode": 't', "PCE": 1.3, "VOT": 67., "cost": '',                
                    "skims": ["GENCOST", "TIME", "DIST"]
                },                    
                {   # 11
                    "name": 'TRKLTOLL',  "mode": 'T', "PCE": 1.3, "VOT": 67., "cost": '@cost_auto',      
                    "skims": ["GENCOST", "TIME", "DIST", "TOLLCOST"]
                },                
                {   # 12
                    "name": 'TRKMGP',   "mode": 'm', "PCE": 1.5, "VOT": 68., "cost": '',                
                    "skims": ["GENCOST", "TIME", "DIST"]
                },                    
                {   # 13
                    "name": 'TRKMTOLL', "mode": 'M', "PCE": 1.5, "VOT": 68., "cost": '@cost_med_truck', 
                    "skims": ["GENCOST", "TIME", "DIST",  "TOLLCOST"]
                }                
            ]

            if period == "MD" and (msa_iteration == 1 or not scenario.mode('D')):
                self.prepare_midday_generic_truck(scenario)

            if msa_iteration > 1:
                # Link and turn flows
                link_attrs = ["auto_volume"]
                turn_attrs = ["auto_volume"]
                for traffic_class in classes:
                    link_attrs.append("@%s" % (traffic_class["name"].lower()))
                    turn_attrs.append("@p%s" % (traffic_class["name"].lower()))
                msa_link_flows = scenario.get_attribute_values("LINK", link_attrs)[1:]
                msa_turn_flows = scenario.get_attribute_values("TURN", turn_attrs)[1:]

            self.run_assignment(period, relative_gap, max_iterations, num_processors, scenario, classes, select_link)

            if msa_iteration > 1:
                link_flows = scenario.get_attribute_values("LINK", link_attrs)
                values = [link_flows.pop(0)]
                for msa_array, flow_array in zip(msa_link_flows, link_flows):
                    msa_vals = numpy.frombuffer(msa_array, dtype='float32')
                    flow_vals = numpy.frombuffer(flow_array, dtype='float32')
                    result = msa_vals + (1 / msa_iteration) * (flow_vals - msa_vals)
                    result_array = array.array('f')
                    result_array.fromstring(result.tostring())
                    values.append(result_array)
                scenario.set_attribute_values("LINK", link_attrs, values)

                turn_flows = scenario.get_attribute_values("TURN", turn_attrs)
                values = [turn_flows.pop(0)]
                for msa_array, flow_array in zip(msa_turn_flows, turn_flows):
                    msa_vals = numpy.frombuffer(msa_array, dtype='float32')
                    flow_vals = numpy.frombuffer(flow_array, dtype='float32')
                    result = msa_vals + (1 / msa_iteration) * (flow_vals - msa_vals)
                    result_array = array.array('f')
                    result_array.fromstring(result.tostring())
                    values.append(result_array)
                scenario.set_attribute_values("TURN", turn_attrs, values)

            self.run_skims(period, num_processors, scenario, classes)
            self.report(period, scenario)

            # Check that the distance matrix is valid (no disconnected zones)
            if raise_zero_dist:
                name = period + "_" + "SOVGP_DIST"
                dist_stats = self._stats[name]
                if dist_stats[1] == 0:
                    zones = scenario.zone_numbers
                    matrix = scenario.emmebank.matrix(name)
                    data = matrix.get_numpy_data(scenario)
                    row, col = numpy.unravel_index(data.argmin(), data.shape)
                    row, col = zones[row], zones[col]
                    raise Exception("Disconnected zone error: 0 value found in matrix %s from zone %s to %s" % (name, row, col))

    def run_assignment(self, period, relative_gap, max_iterations, num_processors, scenario, classes, select_link):
        emmebank = scenario.emmebank

        modeller = _m.Modeller()
        set_extra_function_para = modeller.tool(
            "inro.emme.traffic_assignment.set_extra_function_parameters")
        create_attribute = modeller.tool(
            "inro.emme.data.extra_attribute.create_extra_attribute")
        create_matrix = modeller.tool(
            "inro.emme.data.matrix.create_matrix")
        matrix_calc = modeller.tool(
            "inro.emme.matrix_calculation.matrix_calculator")    
        traffic_assign = modeller.tool(
            "inro.emme.traffic_assignment.sola_traffic_assignment")
        net_calc = gen_utils.NetworkCalculator(scenario)
        
        p = period.lower()
        assign_spec = self.base_assignment_spec(relative_gap, max_iterations, num_processors)
        with _m.logbook_trace("Prepare traffic data for period %s" % period):
            with _m.logbook_trace("Input link attributes"):
                # set extra attributes for the period for VDF
                # ul1 = @time_link
                # ul2 = transig flow -> volad
                # ul3 = @capacity_link
                el1 = "@green_to_cycle"
                el2 = "@auto_volume"              # for skim only
                el3 = "@capacity_inter"       
                set_extra_function_para(el1, el2, el3, emmebank=emmebank)

                # set green to cycle to el1=@green_to_cycle for VDF
                att_name = "@green_to_cycle_%s" % p
                att = scenario.extra_attribute(att_name)
                new_att_name = "@green_to_cycle"
                create_attribute("LINK", new_att_name, att.description, 
                                  0, overwrite=True, scenario=scenario)
                net_calc(new_att_name, att_name, "modes=d")
                # set capacity_inter to el3=@capacity_inter for VDF
                att_name = "@capacity_inter_%s" % p
                att = scenario.extra_attribute(att_name)
                new_att_name = "@capacity_inter"
                create_attribute("LINK", new_att_name, att.description, 
                                  0, overwrite=True, scenario=scenario)
                net_calc(new_att_name, att_name, "modes=d")
                # set link time
                net_calc("ul1", "@time_link_%s" % p, "modes=d")
                net_calc("ul3", "@capacity_link_%s" % p, "modes=d")            
                # set number of lanes (not used in VDF, just for reference)
                net_calc("lanes", "@lane_%s" % p, "modes=d") 

            with _m.logbook_trace("Transit line headway and background traffic"):
                # set headway for the period
                hdw = {"ea": "@headway_op", 
                       "am": "@headway_am",
                       "md": "@headway_op", 
                       "pm": "@headway_pm",
                       "ev": "@headway_op"}
                net_calc("hdw", hdw[p], {"transit_line": "all"})

                # transit vehicle as background flow with periods
                period_hours = {'ea': 3, 'am': 3, 'md': 6.5, 'pm': 3.5, 'ev': 5}
                expression = "60 / (hdw) * vauteq * %s" % (period_hours[p])
                net_calc("ul2", expression, 
                    selections={"link": "all", "transit_line": "hdw=0.01,9999"},
                    aggregation="+")  

            with _m.logbook_trace("Per-class flow attributes"):
                for traffic_class in classes:
                    demand = 'mf"%s_%s"' % (period, traffic_class["name"]) 
                    link_cost = "%s_%s" % (traffic_class["cost"], p) if traffic_class["cost"] else "@cost_operating"

                    att_name = "@%s" % (traffic_class["name"].lower())
                    att_des = "%s %s link volume" % (period, traffic_class["name"])
                    link_flow = create_attribute("LINK", att_name, att_des, 0, overwrite=True, scenario=scenario)
                    att_name = "@p%s" % (traffic_class["name"].lower())
                    att_des = "%s %s turn volume" % (period, traffic_class["name"])
                    turn_flow = create_attribute("TURN", att_name, att_des, 0, overwrite=True, scenario=scenario)

                    class_spec = {
                        "mode": traffic_class["mode"],
                        "demand": demand,
                        "generalized_cost": {
                            "link_costs": link_cost, "perception_factor": 1.0 / traffic_class["VOT"]
                        },
                        "results": {
                            "link_volumes": link_flow.id, "turn_volumes": turn_flow.id,
                            "od_travel_times": None 
                        }
                    }
                    assign_spec["classes"].append(class_spec)
            if select_link:
                with _m.logbook_trace("Prepare for select link analysis"):
                    slink = create_attribute("LINK", "@slink", "selected link", 0, overwrite=True, scenario=scenario)
                    net_calc(slink, "1", select_link)
                    with _m.logbook_trace("Initialize result matrices and extra attributes"):
                        ident = 860
                        for traffic_class, class_spec in zip(classes, assign_spec["classes"]):
                            att_name = "@sel_%s" % (traffic_class["name"].lower())
                            att_des = "%s %s selected link volume"% (period, traffic_class["name"])
                            link_flow = create_attribute("LINK", att_name, att_des, 0, overwrite=True, scenario=scenario)
                            att_name = "@psel_%s" % (traffic_class["name"].lower())
                            att_des = "%s %s selected turn volume" % (period, traffic_class["name"])
                            turn_flow = create_attribute("TURN", att_name, att_des, 0, overwrite=True, scenario=scenario)
                            
                            # TODO: centralize to initialize_matrices (OPEN QUESTION)
                            name = "%s_%s_SELDEM" % (period, traffic_class["name"])
                            desc = "Selected demand for %s %s" % (period, traffic_class["name"])
                            seldem = create_matrix("mf%s" % ident, name, desc, scenario=scenario, overwrite=True)
                            ident += 1

                            # add select link analysis 
                            class_spec["path_analyses"] = [
                                {
                                    "link_component": "@slink",
                                    "turn_component": None,
                                    "operator": ".max.",
                                    "selection_threshold": { "lower": 1, "upper": 1},
                                    "path_to_od_composition": {
                                        "considered_paths": "SELECTED",
                                        "multiply_path_proportions_by": {"analyzed_demand": true, "path_value": false}
                                    },
                                    "analyzed_demand": None,
                                    "results": {
                                        "selected_link_volumes": link_flow.id,
                                        "selected_turn_volumes": turn_flow.id,
                                        "od_values": seldem.name
                                    }
                                }
                            ]
                    
        # Run assignment
        traffic_assign(assign_spec, scenario, chart_log_interval=2)
        return

    def run_skims(self, period, num_processors, scenario, classes):
        modeller = _m.Modeller()
        create_attribute = modeller.tool(
            "inro.emme.data.extra_attribute.create_extra_attribute")
        # matrix_calc = modeller.tool(
        #     "inro.emme.matrix_calculation.matrix_calculator")    
        traffic_assign = modeller.tool(
            "inro.emme.traffic_assignment.sola_traffic_assignment")
        net_calc = gen_utils.NetworkCalculator(scenario)
        emmebank = scenario.emmebank
        p = period.lower()

        with self.setup_skims(period, scenario):
            if period == "MD":
                gen_truck_mode = 'D'
                classes.append({ 
                    "name": 'TRK', "mode": gen_truck_mode, "PCE": 1, "VOT": 67., "cost": '',
                    "skims": ["GENCOST", "TIME", "DIST", "MLCOST", "TOLLCOST"]
                })
            analysis_link = {
                "TIME":     "@auto_time", 
                "DIST":     "length", 
                "HOVDIST":  "@hovdist", 
                "TOLLCOST": "@tollcost",
                "MLCOST":   "@mlcost",
                "TOLLDIST": "@tolldist"
            }
            analysis_turn = {"TIME": "@auto_time_turn"}
            with _m.logbook_trace("Link attributes for skims"):
                create_attribute("LINK", "@hovdist", "distance for HOV", 
                                 0, overwrite=True, scenario=scenario)
                create_attribute("LINK", "@tollcost", "Toll cost in cents", 
                                 0, overwrite=True, scenario=scenario)
                create_attribute("LINK", "@mlcost", "Manage lane cost in cents", 
                                 0, overwrite=True, scenario=scenario)
                create_attribute("LINK", "@tolldist", "Toll distance", 
                                 0, overwrite=True, scenario=scenario)

                net_calc("@hovdist", "length", {"link": "@lane_restriction=2,3"})
                net_calc("@tollcost", "@toll_%s" % p, {"link": "modes=d"})
                net_calc("@mlcost", "@toll_%s" % p, 
                    {"link": "not @toll_%s=0.0 and not @lane_restriction=4" % p})
                net_calc("@tolldist", "length", {"link": "not @toll_%s=0.0" % p})
                # TODO (optional): use temporary link attributes ?
                # link volume in @volau
                create_attribute("LINK", "@auto_volume", "traffic link volume (volau)", 
                                  0, overwrite=True, scenario=scenario)
                create_attribute("LINK", "@auto_time", "traffic link time (timau)", 
                                  0, overwrite=True, scenario=scenario)
                create_attribute("TURN", "@auto_time_turn", "traffic turn time (ptimau)", 
                                  0, overwrite=True, scenario=scenario)
                net_calc("@auto_volume", "volau", {"link": "modes=d"})

                for function in emmebank.functions():
                    if function.type == "VOLUME_DELAY":
                        expression = function.expression
                        for exfpar in ["el1", "el2", "el3"]:
                            expression = expression.replace(exfpar, getattr(emmebank.extra_function_parameters, exfpar))
                        net_calc("@auto_time", expression, {"link": "vdf=%s" % function.id[2:]})
                net_calc("@auto_time_turn", "ptimau*(ptimau.gt.0)",
                         {"incoming_link": "all", "outgoing_link": "all"})

            skim_spec = self.base_assignment_spec(0, 0, num_processors)        
            for traffic_class in classes:
                if not traffic_class["skims"]:
                    continue
                class_analysis = []
                if "GENCOST" in traffic_class["skims"]:
                    od_travel_times = 'mf"%s_%s_%s"' % (period, traffic_class["name"], "GENCOST")
                    traffic_class["skims"].remove("GENCOST")
                else:
                    od_travel_times = None
                for skim_type in traffic_class["skims"]:
                    class_analysis.append({
                        "link_component": analysis_link.get(skim_type),
                        "turn_component": analysis_turn.get(skim_type),
                        "operator": "+",
                        "selection_threshold": {"lower": None, "upper": None},
                        "path_to_od_composition": {
                            "considered_paths": "ALL",
                            "multiply_path_proportions_by": 
                                {"analyzed_demand": False, "path_value": True}
                        },
                        "results": {
                            "od_values": 'mf"%s_%s_%s"' % (period, traffic_class["name"], skim_type),
                            "selected_link_volumes": None,
                            "selected_turn_volumes": None
                        }
                    })
                if traffic_class["cost"]:
                    link_cost = "%s_%s" % (traffic_class["cost"], p)
                else:
                    link_cost = "@cost_operating"
                skim_spec["classes"].append({
                    "mode": traffic_class["mode"],
                    # 0 demand for skim with 0 iteration and fix flow in vdf
                    "demand": 'ms"zero"',
                    "generalized_cost": {
                        "link_costs": link_cost, "perception_factor": 1.0 / traffic_class["VOT"]
                    },
                    "results": {
                        "link_volumes": None, "turn_volumes": None,
                        "od_travel_times": {"shortest_paths": od_travel_times}
                    },
                    "path_analyses": class_analysis,
                })

            # skim assignment
            if self._skim_classes_separately:
                # Debugging check
                skim_classes = skim_spec["classes"][:]
                for kls in skim_classes:
                    skim_spec["classes"] = [kls]
                    traffic_assign(skim_spec, scenario)   
            else:
                traffic_assign(skim_spec, scenario)
        
            # compute diagnal value for TIME and DIST
            with _m.logbook_trace("Compute diagnal values for period %s" % period):
                num_cells = len(scenario.zone_numbers) ** 2
                for traffic_class in classes:
                    class_name = traffic_class["name"]
                    skims = traffic_class["skims"]
                    with _m.logbook_trace("Class %s" % class_name):
                        for skim_type in skims:
                            name = '%s_%s_%s' % (period, class_name, skim_type)
                            matrix = emmebank.matrix(name)
                            data = matrix.get_numpy_data(scenario)
                            if skim_type == "TIME" or skim_type == "DIST":
                                numpy.fill_diagonal(data, 999999999.0)
                                data[numpy.diag_indices_from(data)] = 0.5 * numpy.nanmin(data, 1)
                            else:
                                numpy.fill_diagonal(data, -99999999.0)
                            matrix.set_numpy_data(data, scenario)
                            data = numpy.ma.masked_outside(data, -9999999, 9999999, copy=False)
                            self._stats[name] = (name, data.min(), data.max(), data.mean(), data.sum(), num_cells-data.count())
        return

    def base_assignment_spec(self, relative_gap, max_iterations, num_processors):
        base_spec = {
            "type": "SOLA_TRAFFIC_ASSIGNMENT",
            "background_traffic": {
                "link_component": "ul2",     # ul2 = transit flow of the period
                "turn_component": None,
                "add_transit_vehicles": False
            },                
            "classes": [],
            "stopping_criteria": {
                "max_iterations": max_iterations, "best_relative_gap": 0.0,
                "relative_gap": relative_gap, "normalized_gap": 0.0
            },
            "performance_settings": {"number_of_processors": num_processors},
        }
        return base_spec

    @_context
    def setup_skims(self, period, scenario):
        emmebank = scenario.emmebank
        with _m.logbook_trace("Extract skims for period %s" % period):
            # temp_functions converts to skim-type VDFs
            with gen_utils.temp_functions(emmebank):
                backup_attributes = {"LINK": ["auto_volume", "auto_time", "additional_volume"]}
                with gen_utils.backup_and_restore(scenario, backup_attributes):
                    yield

    def prepare_midday_generic_truck(self, scenario):
        modeller = _m.Modeller()
        create_mode = modeller.tool(
            "inro.emme.data.network.mode.create_mode")
        delete_mode = modeller.tool(
            "inro.emme.data.network.mode.delete_mode")
        change_link_modes = modeller.tool(
            "inro.emme.data.network.base.change_link_modes")
        with _m.logbook_trace("Preparation for generic truck skim"):
            gen_truck_mode = 'D'
            truck_mode = scenario.mode(gen_truck_mode)
            if not truck_mode:
                truck_mode = create_mode(
                    mode_type="AUX_AUTO", mode_id=gen_truck_mode,
                    mode_description="all trucks", scenario=scenario)
            change_link_modes(modes=[truck_mode], action="ADD",
                              selection="modes=vVmMtT", scenario=scenario)
     
    def report(self, period, scenario):
        emmebank = scenario.emmebank
        text = ['<div class="preformat">']
        matrices = [
            "SOVGP_GENCOST",
            "SOVGP_TIME",
            "SOVGP_DIST",
            "SOVTOLL_GENCOST",
            "SOVTOLL_TIME",
            "SOVTOLL_DIST",
            "SOVTOLL_MLCOST",
            "SOVTOLL_TOLLCOST",
            "SOVTOLL_TOLLDIST",
            "HOV2HOV_GENCOST",
            "HOV2HOV_TIME",
            "HOV2HOV_DIST",
            "HOV2HOV_HOVDIST",
            "HOV2TOLL_GENCOST",
            "HOV2TOLL_TIME",
            "HOV2TOLL_DIST",
            "HOV2TOLL_MLCOST",
            "HOV2TOLL_TOLLCOST",
            "HOV2TOLL_TOLLDIST",
            "HOV3HOV_GENCOST",
            "HOV3HOV_TIME",
            "HOV3HOV_DIST",
            "HOV3HOV_HOVDIST",
            "HOV3TOLL_GENCOST",
            "HOV3TOLL_TIME",
            "HOV3TOLL_DIST",
            "HOV3TOLL_MLCOST",
            "HOV3TOLL_TOLLCOST",
            "HOV3TOLL_TOLLDIST",
            "TRKHGP_GENCOST",
            "TRKHGP_TIME",
            "TRKHGP_DIST",
            "TRKHTOLL_GENCOST",
            "TRKHTOLL_TIME",
            "TRKHTOLL_DIST",
            "TRKHTOLL_TOLLCOST",
            "TRKLGP_GENCOST",
            "TRKLGP_TIME",
            "TRKLGP_DIST",
            "TRKLTOLL_GENCOST",
            "TRKLTOLL_TIME",
            "TRKLTOLL_DIST",
            "TRKLTOLL_TOLLCOST",
            "TRKMGP_GENCOST",
            "TRKMGP_TIME",
            "TRKMGP_DIST",
            "TRKMTOLL_GENCOST",
            "TRKMTOLL_TIME",
            "TRKMTOLL_DIST",
            "TRKMTOLL_TOLLCOST",
        ]
        num_cells = len(scenario.zone_numbers) ** 2
        text.append("Number of O-D pairs: %s. Values outside -9999999, 9999999 are masked in summaries.<br>" % num_cells)
        text.append("%-25s %9s %9s %9s %13s %9s" % ("name", "min", "max", "mean", "sum", "mask num"))
        for name in matrices:
            name = period + "_" + name
            matrix = emmebank.matrix(name)
            stats = self._stats.get(name)
            if stats is None:
                data = matrix.get_numpy_data(scenario)
                data = numpy.ma.masked_outside(data, -9999999, 9999999, copy=False)
                stats = (name, data.min(), data.max(), data.mean(), data.sum(), num_cells-data.count())
            text.append("%-25s %9.4g %9.4g %9.4g %13.7g %9d" % stats)
        text.append("</div>")
        title = 'Traffic impedance summary for period %s' % period
        report = _m.PageBuilder(title)
        report.wrap_html('Matrix details', "<br>".join(text))
        _m.logbook_write(title, report.render())

    @_m.method(return_type=unicode)
    def tool_run_msg_status(self):
        return self.tool_run_msg