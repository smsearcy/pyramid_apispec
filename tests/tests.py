# -*- coding: utf-8 -*-
import pytest
from apispec import APISpec
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.scripting import prepare

from pyramid_apispec import __version__
from pyramid_apispec.helpers import add_pyramid_paths

from webtest import TestApp as WebTestApp  # Avoid pytest warning

@pytest.fixture()
def spec():
    return APISpec(
        title="Swagger Petstore",
        version="1.0.0",
        openapi_version="2.0",
        description="This is a sample Petstore server.  You can find out more "
        'about Swagger at <a href="http://swagger.wordnik.com">'
        "http://swagger.wordnik.com</a> or on irc.freenode.net, #swagger."
        'For this sample, you can use the api key "special-key" to test the'
        "authorization filters",
        plugins=[],
    )


def test_version():
    assert "Version" in __version__.__class__.__name__


class TestViewHelpers(object):
    def test_path_from_view(self, spec):
        def hi_request(request):
            return Response("Hi")

        with Configurator() as config:
            config.add_route("hi", "/hi")
            config.add_view(hi_request, route_name="hi")
            config.make_wsgi_app()
        with prepare(config.registry):
            add_pyramid_paths(
                spec,
                "hi",
                operations={
                    "get": {
                        "parameters": [],
                        "responses": {
                            "200": {"description": "Test description", "schema": "file"}
                        },
                    }
                },
            )
        assert "/hi" in spec._paths
        assert "get" in spec._paths["/hi"]
        expected = {
            "parameters": [],
            "responses": {"200": {"description": "Test description", "schema": "file"}},
        }
        assert spec._paths["/hi"]["get"] == expected

    def test_path_from_method_view(self, spec):
        # Class Based Views
        class HelloApi(object):
            """Greeting API.
            ---
            x-extension: global metadata
            """

            def get(self):
                """A greeting endpoint.
                ---
                description: get a greeting
                responses:
                    200:
                        description: said hi
                """
                return "hi"

            def post(self):
                return "hi"

            def mixed(self):
                """Mixed endpoint.
                ---
                description: get a mixed greeting
                responses:
                    200:
                        description: said hi
                """
                return "hi"

        with Configurator() as config:
            config.add_route("hi", "/hi")
            # normally this would be added via @view_config decorator
            config.add_view(HelloApi, attr="get", route_name="hi", request_method="get")
            config.add_view(
                HelloApi, attr="post", route_name="hi", request_method="post"
            )
            config.add_view(
                HelloApi,
                attr="mixed",
                route_name="hi",
                request_method=["put", "delete"],
                xhr=True,
            )
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, "hi")

        expected = {
            "description": "get a greeting",
            "responses": {"200": {"description": "said hi"}},
        }
        assert spec._paths["/hi"]["get"] == expected
        assert "post" in spec._paths["/hi"]
        assert spec._paths["/hi"]["x-extension"] == "global metadata"
        assert "mixed" in spec._paths["/hi"]["put"]["description"]

    def test_autodoc_on(self, spec):
        def hi_request(request):
            return Response("Hi")

        with Configurator() as config:
            config.add_route("hi", "/hi")
            config.add_view(hi_request, route_name="hi")
            config.make_wsgi_app()
        with prepare(config.registry):
            add_pyramid_paths(spec, "hi")
        assert "/hi" in spec._paths
        assert "get" in spec._paths["/hi"]
        assert "head" in spec._paths["/hi"]
        assert "post" in spec._paths["/hi"]
        assert "put" in spec._paths["/hi"]
        assert "patch" in spec._paths["/hi"]
        assert "delete" in spec._paths["/hi"]
        assert "options" in spec._paths["/hi"]
        expected = {"responses": {}}
        assert spec._paths["/hi"]["get"] == expected

    def test_autodoc_on_method(self, spec):
        def hi_request(request):
            return Response("Hi")

        with Configurator() as config:
            config.add_route("hi", "/hi")
            config.add_view(hi_request, route_name="hi", request_method="GET")
            config.make_wsgi_app()
        with prepare(config.registry):
            add_pyramid_paths(spec, "hi")
        assert "/hi" in spec._paths
        assert "get" in spec._paths["/hi"]
        assert list(spec._paths["/hi"].keys()) == ["get"]
        expected = {"responses": {}}
        assert spec._paths["/hi"]["get"] == expected

    def test_autodoc_off_empty(self, spec):
        def hi_request(request):
            return Response("Hi")

        with Configurator() as config:
            config.add_route("hi", "/hi")
            config.add_view(hi_request, route_name="hi")
            config.make_wsgi_app()
        with prepare(config.registry):
            add_pyramid_paths(spec, "hi", autodoc=False)
        assert "/hi" in spec._paths
        assert not spec._paths["/hi"].keys()

    def test_path_with_multiple_methods(self, spec):
        def hi_request(request):
            return Response("Hi")

        with Configurator() as config:
            config.add_route("hi", "/hi")
            config.add_view(hi_request, route_name="hi", request_method=["get", "post"])
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(
                spec,
                "hi",
                operations=dict(
                    get={
                        "description": "get a greeting",
                        "responses": {"200": "..params.."},
                    },
                    post={
                        "description": "post a greeting",
                        "responses": {"200": "..params.."},
                    },
                ),
            )

        get_op = spec._paths["/hi"]["get"]
        post_op = spec._paths["/hi"]["post"]
        assert get_op["description"] == "get a greeting"
        assert post_op["description"] == "post a greeting"

    def test_integration_with_docstring_introspection(self, spec):
        def hello():
            """A greeting endpoint.

            ---
            x-extension: value
            get:
                description: get a greeting
                responses:
                    200:
                        description: a pet to be returned
                        schema:
                            $ref: #/definitions/Pet

            post:
                description: post a greeting
                responses:
                    200:
                        description:some data

            foo:
                description: not a valid operation
                responses:
                    200:
                        description:
                            more junk
            """
            return "hi"

        with Configurator() as config:
            config.add_route("hello", "/hello")
            config.add_view(hello, route_name="hello")
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, "hello")

        get_op = spec._paths["/hello"]["get"]
        post_op = spec._paths["/hello"]["post"]
        extension = spec._paths["/hello"]["x-extension"]
        assert get_op["description"] == "get a greeting"
        assert post_op["description"] == "post a greeting"
        assert "foo" not in spec._paths["/hello"]
        assert extension == "value"

    def test_path_is_translated_to_swagger_template(self, spec):
        def get_pet(pet_id):
            return "representation of pet {pet_id}".format(pet_id=pet_id)

        with Configurator() as config:
            config.add_route("pet", "/pet/{pet_id}")
            config.add_view(get_pet, route_name="pet")
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, "pet")
        assert "/pet/{pet_id}" in spec._paths

    def test_api_prefix(self, spec):
        def api_routes(config):
            config.add_route("pet", "/pet/{pet_id}")

        def get_pet(pet_id):
            return "representation of pet {pet_id}".format(pet_id=pet_id)

        with Configurator() as config:
            config.include(api_routes, route_prefix="/api/v1/")
            config.add_view(get_pet, route_name="pet")
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, "pet")
        assert "/api/v1/pet/{pet_id}" in spec._paths

    def test_routes_with_regex(self, spec):
        def get_pet(pet_id):
            return ""

        with Configurator() as config:
            config.add_route("pet", "/pet/{pet_id:\d+}")
            config.add_view(get_pet, route_name="pet")
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, "pet")
        assert "/pet/{pet_id}" in spec._paths


class TestExplorer(object):
    def test_registration(self):
        with Configurator() as config:
            config.add_route("openapi_spec", "/openapi.json")
            config.include("pyramid_apispec.views")
            config.pyramid_apispec_add_explorer(spec_route_name="openapi_spec")
            app = config.make_wsgi_app()
        introspector = app.registry.introspector
        route_intr = introspector.get("routes", "pyramid_apispec.api_explorer_path")
        assert route_intr.discriminator == "pyramid_apispec.api_explorer_path"

    def test_registration_route_args(self):
        with pytest.raises(ImportError):
            with Configurator() as config:
                config.add_route("openapi_spec", "/openapi.json")
                config.include("pyramid_apispec.views")
                config.pyramid_apispec_add_explorer(
                    spec_route_name="openapi_spec",
                    route_args={"factory": "non_existant_foo.bar.baz"},
                )

    def test_explorer_with_path_arg(self, spec):
        def spec_view(request):
            return spec.to_dict()

        with Configurator() as config:
            config.add_route("openapi_spec", "/api/{version}/openapi.json")
            config.add_view(spec_view, route_name="openapi_spec", renderer='json')

            config.include("pyramid_apispec.views")
            config.pyramid_apispec_add_explorer(
                spec_route_name="openapi_spec",
                explorer_route_path='/api/{version}/api-explorer'
            )
            app = config.make_wsgi_app()

            testapp = WebTestApp(app)
            testapp.get('/api/v1/openapi.json')
            testapp.get('/api/v1/api-explorer')
