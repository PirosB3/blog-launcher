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
        $location.path('/panel/' + btoa(amazonId) + "/" + btoa(amazonSecret));
    }
});

app.controller('PanelController', function($scope, $http, $routeParams) {
    $routeParams
    $http({
        method: "GET",
        url: "/api/instances",
        headers: {
            'amazon-id': atob($routeParams.amazonId),
            'amazon-secret': atob($routeParams.amazonSecret),
        }
    }).then(function(data) {
        debugger;
    });
});
