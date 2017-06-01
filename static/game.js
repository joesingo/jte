function Map(cities_str, airports_str) {

    var cities = JSON.parse(cities_str);
    var airports = JSON.parse(airports_str);

    /*
     * Throw an exception if the provided ID is invalid;
     */
    var checkCityID = function(city_id) {
        if (city_id < 0 || city_id >= cities.length) {
            throw "Invalid city ID";
        }
    }

    /*
     * Return the name of the city with the given ID. Throw an exception if the
     * city does not exist
     */
    this.getCityName = function(city_id) {
        var i = parseInt(city_id);
        checkCityID(i);
        return cities[i].name;
    }

    /*
     * Return the coordinates in the map image for a given city
     */
    this.getCityCoords = function(city_id) {
        var i = parseInt(city_id);
        checkCityID(i);

        return cities[i].coords;
    }

    /*
     * Return the array of cities
     */
    this.getCities = function() {
        return cities;
    }

    this.getAirports = function() {
        return airports;
    }
}

function Game(game_map, canvas) {

    var map = game_map;

    // Store name, city_id pairs so that we can animate player movement
    // when city changes
    var player_locations = {};
    // Store an animation queue for each player, indexed by name
    var player_animations = {};

    var grid = new Grid(canvas);

    grid.settings.background_colour = "black";
    grid.settings.grid_lines = {};
    grid.settings.axes.enabled = false;
    grid.redraw();

    // Draw background image so that it fills the canvas
    var fullscreen_ratio = grid.getUnitsToPx();
    var map_width = canvas.width * fullscreen_ratio;
    var map_height = canvas.height * fullscreen_ratio;
    var background = grid.addImage(images.map, 0, 0, map_width, map_height);
    grid.translate(-0.5*map_width, 0.5*map_height);

    // A list of the current points on the map that can be clicked
    var click_points = [];

    var hovered_click_point = null;

    // Currently pressed keys - indexed by key code
    var keys = {};
    var keyboard_check_timestamp = null;

    var sprites = {
        "player_flags": {},  // indexed by player name
        "click_points": [],
        "located_cities": {},  // indexed by city id for easy removal
        "labels": {},  // indexed by city id also,
        "flight_plan": null
    };

    // Calculate sizes of things in grid units based on size in pixels at
    // fullscreen zoom level
    var sizes = {}
    for (var i in ART_SIZES) {
        sizes[i] = ART_SIZES[i] * fullscreen_ratio * canvas.width / images.map.width;
    }

    // Keep track of zooming for hiding/displaying non-airport city labels
    var zoom_factor = 1;

    /*
     * Convert coordinates in px relative to the map image to grid
     * coordinates
     */
    this.getCoords = function(img_x, img_y) {
        return [map_width * img_x / images.map.width,
                map_height * (1 - img_y) / images.map.height];
    }

    /*
     * Return how many times the zoom level has increased by a factor of
     * ZOOM_THRESHOLD. e.g. if the threshold is 2 then zoom level increases
     * at x2, x4, x8 zoom etc...
     */
    this.getZoomLevel = function(z_factor) {
        return Math.floor(Math.log(z_factor) / Math.log(ZOOM_THRESHOLD));
    }

    /*
     * Hide/unhide labels depending on the zoom level and whether the city
     * is an airport or being located
     */
    this.setLabelVisibility = function() {
        var zoom_level = this.getZoomLevel(zoom_factor);

        for (var city_id in sprites.labels) {
            var obj = grid.getObject(sprites.labels[city_id]);

            // Show all located cities, airport is zoom level > 0, and all
            // cities if zoom level > 1
            if (city_id in sprites.located_cities ||
                ("airport" in obj.data && zoom_level > 0) || zoom_level > 1)
            {
                obj.style.hidden = false;
            }

            // Otherwise label should not be shown
            else {
                obj.style.hidden = true;
            }
        }
    }

    /*
     * Add a text label for each city
     */
    this.addLabels = function() {
        var cities = map.getCities();
        var airports = map.getAirports();

        for (var i=0; i<cities.length; i++) {
            var grid_coords = this.getCoords(cities[i].coords[0], cities[i].coords[1]);
            grid_coords[1] += 1.5 * sizes.city_radius;
            var id = grid.addText(cities[i].name.toUpperCase(), grid_coords[0], grid_coords[1],
                                  "center", LABEL_STYLE);

            sprites.labels[i] = id;

            // Initially hide everything since only airport labels will be
            // shown
            var obj = grid.getObject(id);
            obj.style.hidden = true;
        }

        // Set a flag in airport objects so they can be recognised in
        // setLabelVisibility()
        for (var i=0; i<airports.length; i++) {
            var obj = grid.getObject(sprites.labels[airports[i]]);
            obj.data.airport = true;
        }
    }

    /*
     * Add a player flag to the grid and add the object ID to the
     * sprites.player_flags. Return an array continaing the grid.js object
     * IDs of the shapes created
     */
    this.addPlayerFlag = function(name, colour, city) {

        var img_coords = map.getCityCoords(city);
        var grid_coords = this.getCoords(img_coords[0], img_coords[1]);

        var points = [];
        var x = grid_coords[0] - 0.5*sizes.flagpole_width;
        var y = grid_coords[1];
        points.push([x, y]);
        y += sizes.flagpole_height;
        points.push([x, y]);
        x += sizes.flagpole_width;
        points.push([x, y]);
        x += sizes.flag_size;
        points.push([x, y]);
        y -= sizes.flag_size;
        points.push([x, y]);
        x -= sizes.flag_size;
        points.push([x, y]);
        y = grid_coords[1];
        points.push([x, y]);

        var id = grid.addShape(points, {"colour": colour, "fill": true});
        var id2 = grid.addShape(points, {"colour": "white", "fill": false,
                                         "line_width": 2});
        sprites.player_flags[name] = [id, id2];
        return [id, id2];
    }

    /*
     * Add a marker at the coordinates of a city. marker_style is one of
     * LOCATING_MARKER or TRAVEL_MARKER. Return an array continaing the grid.js object
     * IDs of the shapes created
     */
    this.addCityMarker = function(coords, marker_style, airport) {
        var border_id;
        var inner_id;

        var c = MARKER_COLOURS[(airport ? "airport" : marker_style)];
        var border_style = {"colour": c.border, "fill": true};
        var inner_style = {"colour": c.inner, "fill": true};

        switch (marker_style) {
            case TRAVEL_MARKER:
                border_id = grid.addCircle(coords[0], coords[1], sizes.city_radius,
                                           border_style);

                inner_id = grid.addCircle(coords[0], coords[1],
                                          sizes.city_radius - sizes.city_border_width,
                                          inner_style);
                break

            case LOCATING_MARKER:
                // m is how many times bigger to draw locating marker
                // compared to travel marker
                var m = 2.7;
                // Number of sides of the star
                var sides = 5;
                var points = [[], []];

                for (var j=0; j<2; j++) {
                    var r1 = sizes.city_radius * m;

                    if (j == 1) {
                        r1 -= sizes.city_border_width * m;
                    }

                    var r2 = 0.5 * r1;

                    for (var i=0; i<2*sides; i++) {
                        // Outer points of star are on a circle radius r1
                        var angle1 = 0.5 * Math.PI + i * 2 * Math.PI / sides;
                        // Inner points are on a circle radius 2 and angle is
                        // offset by half the change in angle1
                        var angle2 = angle1 + Math.PI / sides;
                        points[j].push([
                            coords[0] + r1 * Math.cos(angle1),
                            coords[1] + r1 * Math.sin(angle1)]);

                        points[j].push([
                            coords[0] + r2 * Math.cos(angle2),
                            coords[1] + r2 * Math.sin(angle2)]);
                    }
                }

                border_id = grid.addShape(points[0], border_style);
                inner_id = grid.addShape(points[1], inner_style);

                break;
        }

        return [border_id, inner_id];
    }

    /*
     * Return the step function to animate a player flag moving along the
     * direction vector provided. It is assumed that the animation will be
     * run with the parameter going from 0 to 1. When the animation finished
     * the next one in the queue is run (if there is one)
     */
    this.flagAnimationStepFunction = function(player_name, object_ids, direction) {

        // Store the starting coordinates of each point in each shape in the
        // flag
        var initial_coords = [];
        for (var i=0; i<object_ids.length; i++) {
            var obj = grid.getObject(object_ids[i]);
            initial_coords.push([]);

            for (var j=0; j<obj.data.points.length; j++) {
                initial_coords[i].push(obj.data.points[j]);
            }
        }

        var g = this;

        return function(t) {
            for (var i=0; i<object_ids.length; i++) {
                var obj = grid.getObject(object_ids[i]);

                for (var j=0; j<obj.data.points.length; j++) {
                    obj.data.points[j] = [
                        initial_coords[i][j][0] + t * direction[0],
                        initial_coords[i][j][1] + t * direction[1]
                    ];
                }
            }

            // If at the end of this animation, remove animation from queue
            // and run next one
            if (t == 1) {
                player_animations[player_name].shift();  // remove 1st element

                if (player_animations[player_name].length > 0) {
                    g.runNextAnimation(player_name);
                }
            }
        };
    }

    /*
     * Start the next animation in the queue for the specified player
     */
    this.runNextAnimation = function(player_name) {

        var d = player_animations[player_name][0];

        // Remove any current flags belonging to this player
        grid.removeObject(sprites.player_flags[player_name][0]);
        grid.removeObject(sprites.player_flags[player_name][1]);

        // Add a flag at the 'from' city
        var ids = this.addPlayerFlag(player_name, d.colour, d.from);

        // Calculate the 'from' and 'to' coordinates and direction vector
        var f_img_coords = map.getCityCoords(d.from);
        var t_img_coords = map.getCityCoords(d.to);
        var f_coords = this.getCoords(f_img_coords[0], f_img_coords[1]);
        var t_coords = this.getCoords(t_img_coords[0], t_img_coords[1]);
        var direction = [t_coords[0] - f_coords[0],
                         t_coords[1] - f_coords[1]];

        grid.runAnimation(this.flagAnimationStepFunction(player_name, ids, direction), 0, 1,
                          1 / ANIMATION_TIME);
    }

    /*
     * Update the player list and draw flags on the canvas
     */
    this.drawPlayers = function(status) {

        for (var i=0; i<status.players.length; i++) {

            var $name_span = $("<span>", {"class": "player-name"});
            $name_span.text(status.players[i].name);

            if (name == status.current_player) {
                $name_span.addClass("current-player");
            }

            var text = map.getCityName(status.players[i].current_city) +
                                       " (" + status.players[i].progress +
                                       ")";

            var $item = $("<li>", {"css": {"background": COLOURS[i]}});
            $item.append($name_span, "<br />", text);

            // Make a list of player'c cities
            var $city_list = $("<ul>").addClass("opponent-city-list");
            for (var j=0; j<status.players[i].cards.length; j++) {
                var city_name = map.getCityName(status.players[i].cards[j].id);
                var $li = $("<li>").text(city_name);

                if (status.players[i].cards[j].visited) {
                    $li.addClass("visited");
                }

                $city_list.append($li);
            }

            $item.append($city_list);

            $("#player-list").append($item);

            // Draw player flag if they were not drawn previously
            if (!(status.players[i].name in player_locations)) {
                this.addPlayerFlag(status.players[i].name, COLOURS[i],
                                   status.players[i].current_city);
            }
            // If player was drawn previously but in a different city, then
            // animate the movement
            else if (player_locations[status.players[i].name] != status.players[i].current_city)
            {
                if (!(status.players[i].name in player_animations)) {
                    player_animations[status.players[i].name] = [];
                }

                // Add animation to queue
                player_animations[status.players[i].name].push({
                    "from": player_locations[status.players[i].name],
                    "to": status.players[i].current_city,
                    "colour": COLOURS[i]
                });

                // If we have just put the only animation in the queue then
                // it can be run straight away
                if (player_animations[status.players[i].name].length == 1) {
                    this.runNextAnimation(status.players[i].name);
                }
            }
        }

        // Update player_locations
        player_locations = {};
        for (var i=0; i<status.players.length; i++) {
            player_locations[status.players[i].name] = status.players[i].current_city;
        }

        // Remove any flags for players no longer in the game
        for (var name in sprites.player_flags) {
            if (!(name in player_locations)) {
                grid.removeObject(sprites.player_flags[name][0]);
                grid.removeObject(sprites.player_flags[name][1]);

                delete sprites.player_flags[name];
            }
        }
        grid.redraw();
    }

    /*
     * Update the player's cards showing which have been visited
     */
    this.drawCards = function(status) {
        // Remove previous city markers
        for (var city_id in sprites.located_cities) {
            this.hideCityLocation(city_id);
        }

        for (let i=0; i<status.my_cards.length; i++) {
            var $li = $("<li>").append(map.getCityName(status.my_cards[i].id));

            if (status.my_cards[i].visited) {
                $li.addClass("visited");
            }
            // Show location on the map if not already visited
            else {
                this.showCityLocation(status.my_cards[i].id);
            }

            $("#card-list").append($li);

        }
    }

    /*
     * Show the available actions to the user
     */
    this.drawActions = function(status) {
        // Keep track of whether there are any air links so we can draw the
        // flight plan if so
        var air_link = false;

        for (let i=0; i<status.actions.length; i++) {

            switch (status.actions[i].type) {
                case ROLL_DICE_ACTION:
                    // Show button, remove previous click handlers, and add
                    // new click handler to perform action
                    $("#roll-dice-button").show().off("click")
                                          .on("click",function() {
                        performAction(status.actions[i].id);
                        $(this).hide();
                    });
                    break;

                case TRAVEL_ACTION:
                    var city_id = status.actions[i].link.to_city;
                    var city_name = map.getCityName(city_id);
                    var type = status.actions[i].link.type;

                    var img_coords = map.getCityCoords(city_id);
                    var coords = this.getCoords(img_coords[0], img_coords[1]);
                    var airport = (map.getAirports().indexOf(city_id) >= 0);
                    var ids = this.addCityMarker(coords, TRAVEL_MARKER, airport);
                    sprites.click_points.push(ids)

                    if (!(city_id in click_points)) {
                        click_points[city_id] = {"coords": coords,
                                                 "actions": []};
                    }
                    click_points[city_id].actions.push({
                        "id": status.actions[i].id,
                        "link_type": type
                    });

                    if (type == AIR_LINK) {
                        air_link = true;
                    }
                    break;

                case WAIT_AT_PORT_ACTION:
                    $("#wait-at-port-button").show().off("click")
                                             .on("click", function() {
                        performAction(status.actions[i].id);
                        $(this).hide();
                    })
                    break;
            }
        }

        if (air_link) {
            this.showFlightPlan();
        }
    }

    /*
     * Return the click point object at (x, y) or null if no such point
     * exists
     */
    this.getClickPoint = function(x, y) {
        for (var i in click_points) {
            var cx = click_points[i].coords[0];
            var cy = click_points[i].coords[1];
            var distance = Math.sqrt(Math.pow(x - cx, 2) + Math.pow(y - cy, 2));

            if (distance <= sizes.city_radius) {
                return click_points[i];
            }
        }

        return null;
    }

    /*
     * Remove and re-add the grid object with the specified ID, and return
     * the new ID (this is used to put this object lower in the draw order)
     */
    this.reAddObject = function(id) {
        var obj = grid.getObject(id);
        grid.removeObject(id);
        return grid.addObject(obj.type, obj.data, obj.style);
    }

    this.showCityLocation = function(city_id) {
        var img_coords = map.getCityCoords(city_id);
        var grid_coords = this.getCoords(img_coords[0], img_coords[1]);
        var ids = this.addCityMarker(grid_coords, LOCATING_MARKER, false);
        sprites.located_cities[city_id] = ids;

        // Re-set labels so that this label will definitely be shown
        this.setLabelVisibility();
        grid.redraw();
    }

    this.hideCityLocation = function(city_id) {
        var ids = sprites.located_cities[city_id];
        for (var i=0; i<ids.length; i++) {
            grid.removeObject(ids[i]);
        }
        delete sprites.located_cities[city_id];
        this.setLabelVisibility();
        grid.redraw();
    }

    this.showFlightPlan = function() {
        if (sprites.flight_plan === null) {
            sprites.flight_plan = grid.addImage(images.flight_plan, 0, 0, map_width,
                                                map_height);
        }
    }

    this.hideFlightPlan = function() {
        if (sprites.flight_plan !== null) {
            grid.removeObject(sprites.flight_plan);
            grid.redraw();
            sprites.flight_plan = null;
        }
    }

    /*
     * Check which keys are currently pressed and perform the appropriate actions
     */
    this.keyboardCheckLoop = function(timestamp) {
        if (keyboard_check_timestamp === null) {
            keyboard_check_timestamp = timestamp;
        }

        var dt = (timestamp - keyboard_check_timestamp) / 1000;

        // Work out speed per second in GRID UNITS
        var speed = SCROLL_SPEED * grid.getUnitsToPx();

        if ("d" in keys) {
            grid.translate(-speed * dt, 0);
        }
        else if ("a" in keys) {
            grid.translate(speed * dt, 0);
        }

        if ("w" in keys) {
            grid.translate(0, -speed * dt);
        }
        else if ("s" in keys) {
            grid.translate(0, speed * dt);
        }

        keyboard_check_timestamp = timestamp;
        window.requestAnimationFrame(g.keyboardCheckLoop);
    }

    /*
     * Clear the game canvas and update the player list, cards, and canvas
     */
    this.updateDisplay = function(status) {
        if (!status.in_progress) {
            $("#end-game-popup b").text(status.winner);
            showPopup("end-game-popup");
        }

        // Update message log
        for (var i=0; i<status["message_log"].length; i++) {
            var msg = status["message_log"][i];

            var $msgs = $("#right-panel .game-message");

            if ($msgs.length == 0 ||
                msg["timestamp"] > $msgs.last().data("timestamp")) {

                var $msg_p = $("<p>", {"class": "message game-message"});
                $msg_p.data("timestamp", msg["timestamp"]);
                $msg_p.text(msg["message"]);

                $("#right-panel").append($msg_p);
            }
        }
        // Scroll to the bottom of the log
        $("#right-panel")[0].scrollTop = $("#right-panel")[0].scrollHeight;

        this.hideFlightPlan();

        // Remove city circles
        for (var i=0; i<sprites.click_points.length; i++) {
            grid.removeObject(sprites.click_points[i][0]);
            grid.removeObject(sprites.click_points[i][1]);
        }
        sprites.click_points = [];

        click_points = [];
        hovered_click_point = null;

        // Show cards
        $("#card-list").text("");
        this.drawCards(status);

        if ("actions" in status) {
            this.drawActions(status);

            if (status.dice_points) {
                $("#dice-points").prop("src", `/static/dice/${status.dice_points}.png`).show();
            }
        }

        $("#player-list").text("");
        this.drawPlayers(status);

        // Re-add labels so they are not hidden behind city markers or flags
        for (var city_name in sprites.labels) {
            sprites.labels[city_name] = this.reAddObject(sprites.labels[city_name]);
        }

        grid.redraw();

        // Show canvas and set the height of the message log area on the
        // first update
        if ($("#right-panel").is(":hidden")) {
            var h = $("#left-panel").height() - $("#card-list").height();
            $("#right-panel").height(h).show();
            canvas.style.display = "inline";
        }

        $("#loading-gif").hide();
    }

    var g = this;
    canvas.addEventListener("mousemove", function(e) {
        var grid_coords = grid.fromCanvasCoords(e.offsetX, e.offsetY);

        var click_point = g.getClickPoint(grid_coords[0], grid_coords[1]);

        if (click_point) {
            hovered_click_point = click_point;
            document.body.style.cursor = "pointer";
        }
        // Unhover if a point was previously hovered but is not now
        else if (hovered_click_point) {
            hovered_click_point = null;
            document.body.style.cursor = "default";
        }
    });

    canvas.addEventListener("click", function(e) {
        if (hovered_click_point) {

            // Perform action straigt away if there is only one for this
            // click point...
            if (hovered_click_point.actions.length == 1) {
                performAction(hovered_click_point.actions[0].id);
            }
            // ...otherwise show popup so that user can choose
            else {
                var $list = $("#action-choice-popup ul");
                $list.text("");

                for (let i=0; i<hovered_click_point.actions.length; i++) {
                    var type = hovered_click_point.actions[i].link_type;
                    var $button = $("<button>", {"text": `Travel by ${type}`})
                    let id = hovered_click_point.actions[i].id;

                    $button.on("click", function() {
                        performAction(id);
                        hidePopup("action-choice-popup");
                    });

                    $list.append($("<li>").append($button));
                }

                showPopup("action-choice-popup");
            }

            // Reset cursor once clicked
            document.body.style.cursor = "default";
        }
    });

    // Add event listeners to keep track of which keys are currently pressed
    window.addEventListener("keydown", function(e) {
        var key = e.key.toLowerCase();
        keys[key] = true;
    });
    window.addEventListener("keyup", function(e) {
        var key = e.key.toLowerCase();
        delete keys[key];
    });

    /*
     * Add callback function to grid zooming to redraw labels when zoom level
     * changes
     */
    grid.settings.zoom.callback = function(zoom, x, y) {
        var prev_level = g.getZoomLevel(zoom_factor);
        var new_level = g.getZoomLevel(zoom_factor * (1 + zoom));

        // Prevent zooming too far out or in
        if (new_level < -1 || new_level > 2) {
            return false;
        }

        zoom_factor *= 1 + zoom;

        // Re-calculate which labels to show if there has been a change in
        // level
        if (prev_level != new_level) {
            g.setLabelVisibility();
        }

        return true;
    }

    // Toggle flight plan on button press
    $("#flight-plan-button").on("click", function() {
        if (sprites.flight_plan === null) {
            g.showFlightPlan();
        }
        else {
            g.hideFlightPlan();
        }
    });

    this.addLabels();
    this.keyboardCheckLoop(0);
}

/*
 * Show a semi-opaque rectangle to gray out the screen and show a fixed
 * position popup
 */
function showPopup(id) {
    $("#gray-screen").show();
    $("#" + id).show();
}
function hidePopup(id) {
    $("#gray-screen").hide();
    $("#" + id).hide();
}

/*
 * Send an AJAX request to perform the specified action. Immediately update
 * status if the request is successful
 */
function performAction(action_id) {
    // Hide buttons and show loading gif
    $("#buttons-bar .actions").children().hide();
    $("#loading-gif").show();

    $.ajax(ACTION_URL, {
        "method": "POST",
        "data": {
            "action_id": action_id
        },
        "error": function(request, status, error) {
            throw "Unexpected error performing action";
        },
        "success": function(response, status, request) {
            getStatus();
        }
    });
}

/*
 * Send an AJAX request to be updated on the current status of the game
 */
function getStatus() {
    $.ajax(STATUS_URL + latest_timestamp + "/", {
        "method": "GET",
        "error": function(request, status, error) {
            throw "Unexpected error retrieving status";
        },
        "success": function(response, status, request) {
            // $("#debug-area").text(response);

            // Only update if the response was 200 (i.e. something new
            // has happened)
            if (request.status == 200) {
                var game_status = JSON.parse(response);
                latest_timestamp = game_status.timestamp;

                game.updateDisplay(game_status);
            }
        }
    });
}

/*
 * Set the size and position of the provided canvas to maintain aspect ratio
 * of map image and fill width or height of available space
 */
function setCanvasSize(canvas) {

    // Position canvas wrapper between players and card list, taking up all
    // vertical space
    $("#canvas-wrapper").css({
        "top": $("#player-list").height(),
        "bottom": $("#card-list").height()
    });

    // Set canvas to size 0 so it does not affect #left-panel size
    canvas.width = 0;
    canvas.height = 0;

    var max_width = $("#left-panel").width();
    var max_height = $("#canvas-wrapper").height();

    // Fill all available width and set height to maintain aspect ratio
    canvas.width = max_width;
    canvas.height = images.map.height * canvas.width / images.map.width;

    // If canvas height exceeds the height of the left panel then fit the
    // height exactly instead
    if (canvas.height > max_height) {
        canvas.height = max_height;
        canvas.width = images.map.width * canvas.height / images.map.height;
    }

    // Center the canvas
    var top_px = 0.5 * (max_height - canvas.height);
    var left_px = 0.5 * (max_width - canvas.width);

    canvas.style.top = top_px + "px";
    canvas.style.left = left_px + "px";

    // Position buttons over canvas
    $("#buttons-bar").css({
        "top": 3 + top_px,
        "left": 3 + left_px,
        "right": 3 - left_px
    });
}

const UPDATE_INTERVAL = 1000;

const ROLL_DICE_ACTION = "roll_dice";
const TRAVEL_ACTION = "travel";
const WAIT_AT_PORT_ACTION = "wait_at_port";

const LAND_LINK = "land";
const SEA_LINK = "sea";
const AIR_LINK = "air";

// The length of the player movement animation in seconds
const ANIMATION_TIME = 0.7;

// The different styles of circles at cities
const LOCATING_MARKER = "locating";
const TRAVEL_MARKER = "travlel";

var MARKER_COLOURS = {};
MARKER_COLOURS[LOCATING_MARKER] = {
    "border": "black",
    "inner": "yellow"
}
MARKER_COLOURS[TRAVEL_MARKER] = {
    "border": "white",
    "inner": "black"
}
MARKER_COLOURS.airport = {
    "border": "white",
    "inner": "red"
}

const COLOURS = ["#AA3939", "#226666", "#AA8439"];

const ZOOM_THRESHOLD = 2.2;

// Speed in px/sec for scrolling the map with WASD keys
const SCROLL_SPEED = 600;

var STATUS_URL = window.location.pathname + "status/";
var ACTION_URL = window.location.pathname + "action/";

// Sizes of art assets in px relative to the size of the map image file.
// This is needed so that the assets can be drawn at the correct relative size
// regardless of zoom level and canvas size
var ART_SIZES = {
    "flagpole_width": 6,
    "flagpole_height": 30,
    "flag_size": 15,

    "city_radius": 8,
    "city_border_width": 3,

    "initial_label_size": 30,  // Font height
}

var images = {};
images.map = new Image();
images.map.src = "/static/europe.png";

images.flight_plan = new Image();
images.flight_plan.src = "/static/flight-plan.png";

var cities_str = document.getElementById("cities").innerHTML;
var airports_str = document.getElementById("airports").innerHTML;
cities_str = cities_str.replace(/&#34;/g, '"');
airports_str = airports_str.replace(/&#34;/g, '"');
var map = new Map(cities_str, airports_str);

var latest_timestamp = 1.1;

var canvas = $("#game-canvas")[0];
// Hide canvas until first update to avoid seeing things labels before they
// are hidden etc...
canvas.style.display = "none";

// Hide right panel where message log appears so that we can tell in the
// first call to updateDisplay() and set it to be the same height as the
// left panel
$("#right-panel").hide();

var ctx = canvas.getContext("2d");

var LABEL_STYLE = {
    "colour": "white",
    "font": "VT323, monospace",
    "font_size": null  // This is set once the map image loads
};

var game;

function start_game() {
    setCanvasSize(canvas);

    // Disable image smoothing so that map is not blurry when zoomed in
    ctx.mozImageSmoothingEnabled = false;
    ctx.webkitImageSmoothingEnabled = false;
    ctx.msImageSmoothingEnabled = false;
    ctx.imageSmoothingEnabled = false;

    LABEL_STYLE.font_size = ART_SIZES.initial_label_size * canvas.width / images.map.width;

    game = new Game(map, canvas);

    // Get the status and start the update loop
    getStatus();
    window.setInterval(getStatus, UPDATE_INTERVAL);
}

// Don't start game until all images are loaded
var loaded_images = 0;
for (let i in images) {
    images[i].onload = function() {
        loaded_images++;

        if (loaded_images == Object.keys(images).length) {
            start_game();
        }
    }
}