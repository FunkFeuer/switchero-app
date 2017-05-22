#!/usr/bin/env node
var PORT = process.env.PORT || 8080;
var AUTHENTICATION_FILE = process.env.AUTHENTICATION_FILE || "htpasswd";
var AUTHORIZATION_FILE = process.env.AUTHORIZATION_FILE || "authorization.csv";
var ENDPOINT_FILE = process.env.ENDPOINT_FILE || "endpoint.csv";
var PROTO_FILE = process.env.PROTO_FILE || "switchero.proto";


var wait = require("wait.for");
var csv = require("fast-csv");
var httpauth = require("http-auth");
var shirotrie = require("shiro-trie");
var express = require("express");
var morgan = require("morgan");
var bodyparser = require("body-parser");
var grpc = require("grpc");
var _ = require("underscore");


wait.launchFiber(function () {
  console.log("Starting");

  // Load Authorizations
  var authorize = wait.for(function (callback) {
    var authorize = shirotrie.new();
    csv
      .fromPath(AUTHORIZATION_FILE, { headers: true })
      .on("data", function(data) {
        authorize.add(data["user"] + ":" + data["locator"]);
      })
      .on("end", function() {
        callback(null, authorize);
      });
  });

  // Load RPC endpoints
  var rpc_endpoints = wait.for(function (callback) {
    var rpc_endpoints = {};
    var proto = grpc.load(PROTO_FILE).switchero;
    csv
      .fromPath(ENDPOINT_FILE, { headers: true })
      .on("data", function(data) {
        rpc_endpoints[data["locator"]] = new proto.Switchero(data["rpc_endpoint"], grpc.credentials.createInsecure());
      })
      .on("end", function() {
        callback(null, rpc_endpoints);
      });
  });

  // Load Express app
  var app = express();

  // Logging
  app.use(morgan("combined"))

  // Authentication
  app.use(httpauth.connect(httpauth.basic({ realm: "switchero", file: AUTHENTICATION_FILE })))

  // Get locator and change to : format
  app.use(/^\/(.+)/, function (req, res, next) {
    req.locator = req.params[0].replace(/\//g, ":");
    next();
  })

  // Authorization
  app.use(/^\/(.+)/, function (req, res, next) {
    if (!authorize.check(req.user + ":" + req.locator)) {
      res.sendStatus(401);
      return;
    }
    next();
  })

  // Check if RPC endpoint exists
  app.use(/^\/(.+)/, function (req, res, next) {
    req.rpc_endpoint = rpc_endpoints[req.locator];
    if (req.rpc_endpoint == null) {
      res.sendStatus(404);
      return;
    }
    next();
  })

  // Parse body as text
  app.use(bodyparser.text({ type: "*/*" }))

  // GET method
  app.get(/^\/(.+)/, function (req, res) {
    var locator = req.locator;

    req.rpc_endpoint.powerStatus({ locator: locator }, function(err, response) {
      if (err) {
        res.sendStatus(500);
        return;
      }

      if ("error" in response && "NOT_FOUND" == response["error"]) {
        res.sendStatus(404);
        return;
      }

      res.contentType("application/json");
      payload = { state: response["state"] };
      if (response["cap_measure"]) {
        _.extend(payload, {
          state: response["state"],
          volts: response["volts"],
          amps: response["amps"],
          watts: response["watts"],
          pf: response["pf"]
        });
      }
      if (response["cap_fault"]) {
        _.extend(payload, {
          fault: response["fault"]
        })
      }
      res.send(payload);
    });
  })

  // POST method
  app.post(/^\/(.+)/, function (req, res) {
    var locator = req.locator;
    var state = req.body;

    if (state != "ON" && state != "OFF") {
      res.sendStatus(400);
      return;
    }

    var remoteCall = function(err, response) {
      if (err) {
        res.sendStatus(500);
        return;
      }

      if ("error" in response && "NOT_FOUND" == response["error"]) {
        res.sendStatus(404);
        return;
      }

      res.contentType("text/plain");
      res.send(state).send();
    }
    if (state == "ON") {
      req.rpc_endpoint.powerOn({ locator: locator }, remoteCall);
    } else if (state == "OFF") {
      req.rpc_endpoint.powerOff({ locator: locator }, remoteCall);
    }
  })

  app.disable("x-powered-by")
  var server = app.listen(PORT, function () {
    console.log("Listening on [%s]:%d", server.address().address, server.address().port)
  })
})
