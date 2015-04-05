var app = angular.module('bitnami', ['ngRoute']);

app.config(function($routeProvider, $locationProvider) {
    $routeProvider
        .when('/', {
            templateUrl: '/static/templates/credentials.html',
            controller: 'CredentialsController',
        })
        .when('/panel/:amazonId/:amazonSecret', {
            templateUrl: '/static/templates/panel.html',
            controller: 'PanelController',
        })
});

app.controller('CredentialsController', function($scope, $location) {
    $scope.processForm = function() {
        var amazonId = $scope.amazonId;
        var amazonSecret = $scope.amazonSecret;

        // The most unsecure authentication method ever..
        $location.path('/panel/' + btoa(amazonId) + "/" + btoa(amazonSecret));
    }
});

app.controller('PanelController', function($interval, $scope, $http, $routeParams, $location) {
    $scope.runningRequest = null;

    $scope.startInstance = function(instanceName) {
        if ($scope.servers[instanceName]) {
            $scope.runningRequest = true;
            $http({
                method: "UPDATE",
                url: "/api/instances/" + instanceName,
                headers: {
                    'amazon-id': atob($routeParams.amazonId),
                    'amazon-secret': atob($routeParams.amazonSecret),
                }
            }).then(function(res) {
                $scope.runningRequest = false;
                $scope.reloadServers();
            }, function(reason) {
                alert("Invalid AWS credentials for North California");
                $location.path('/');
            });
        }
    }

    $scope.createInstance = function() {
        $scope.runningRequest = true;
        $http({
            method: "CREATE",
            url: "/api/instances",
            headers: {
                'amazon-id': atob($routeParams.amazonId),
                'amazon-secret': atob($routeParams.amazonSecret),
            }
        }).then(function(res) {
            $scope.runningRequest = false;
            $scope.reloadServers();
        }, function(reason) {
            alert("Invalid AWS credentials for North California");
            $location.path('/');
        });
    }

    $scope.stopInstance = function(instanceName) {
        if ($scope.servers[instanceName]) {
            $scope.runningRequest = true;
            $http({
                method: "DELETE",
                url: "/api/instances/" + instanceName,
                headers: {
                    'amazon-id': atob($routeParams.amazonId),
                    'amazon-secret': atob($routeParams.amazonSecret),
                }
            }).then(function(res) {
                $scope.runningRequest = false;
                $scope.reloadServers();
            }, function(reason) {
                alert("Invalid AWS credentials for North California");
                $location.path('/');
            });
        }
    }

    $scope.reloadServers = function() {
        $http({
            method: "GET",
            url: "/api/instances",
            headers: {
                'amazon-id': atob($routeParams.amazonId),
                'amazon-secret': atob($routeParams.amazonSecret),
            }
        }).then(function(res) {
            $scope.servers = res.data;
        }, function(reason) {
            alert("Invalid AWS credentials for North California");
            $location.path('/');
        });
    }

    // Every 3 seconds update server state
    $interval($scope.reloadServers, 1000 * 3);
    $scope.reloadServers();
});
