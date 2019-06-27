from collections import OrderedDict
from unittest import TestCase

from mock import patch

from samcli.commands.local.lib.api_provider import ApiProvider, SamApiProvider, CfnApiProvider


class TestApiProvider_init(TestCase):

    @patch.object(ApiProvider, "_extract_apis")
    @patch("samcli.commands.local.lib.api_provider.SamBaseProvider")
    def test_provider_with_valid_template(self, SamBaseProviderMock, extract_api_mock):
        extract_api_mock.return_value = {"set", "of", "values"}

        template = {"Resources": {"a": "b"}}
        SamBaseProviderMock.get_template.return_value = template

        provider = ApiProvider(template)

        self.assertEquals(len(provider.apis), 3)
        self.assertEquals(provider.apis, set(["set", "of", "values"]))
        self.assertEquals(provider.template_dict, {"Resources": {"a": "b"}})
        self.assertEquals(provider.resources, {"a": "b"})


class TestApiProviderSelection(TestCase):
    def test_api_provider_sam_api(self):
        resources = {
            "TestApi": {
                "Type": "AWS::Serverless::Api",
                "Properties": {
                    "StageName": "dev",
                    "DefinitionBody": {
                        "paths": {
                            "/path": {
                                "get": {
                                    "x-amazon-apigateway-integration": {
                                        "httpMethod": "POST",
                                        "type": "aws_proxy",
                                        "uri": {
                                            "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31"
                                                       "/functions/${NoApiEventFunction.Arn}/invocations",
                                        },
                                        "responses": {},
                                    },
                                }
                            }

                        }
                    }
                }
            }
        }

        provider = ApiProvider.find_api_provider(resources)
        self.assertTrue(isinstance(provider, SamApiProvider))

    def test_api_provider_sam_function(self):
        resources = {
            "TestApi": {
                "Type": "AWS::Serverless::Function",
                "Properties": {
                    "StageName": "dev",
                    "DefinitionBody": {
                        "paths": {
                            "/path": {
                                "get": {
                                    "x-amazon-apigateway-integration": {
                                        "httpMethod": "POST",
                                        "type": "aws_proxy",
                                        "uri": {
                                            "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31"
                                                       "/functions/${NoApiEventFunction.Arn}/invocations",
                                        },
                                        "responses": {},
                                    },
                                }
                            }

                        }
                    }
                }
            }
        }

        provider = ApiProvider.find_api_provider(resources)

        self.assertTrue(isinstance(provider, SamApiProvider))

    def test_api_provider_cloud_formation(self):
        resources = {
            "TestApi": {
                "Type": "AWS::ApiGateway::RestApi",
                "Properties": {
                    "StageName": "dev",
                    "Body": {
                        "paths": {
                            "/path": {
                                "get": {
                                    "x-amazon-apigateway-integration": {
                                        "httpMethod": "POST",
                                        "type": "aws_proxy",
                                        "uri": {
                                            "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31"
                                                       "/functions/${NoApiEventFunction.Arn}/invocations",
                                        },
                                        "responses": {},
                                    },
                                }
                            }

                        }
                    }
                }
            }
        }

        provider = ApiProvider.find_api_provider(resources)
        self.assertTrue(isinstance(provider, CfnApiProvider))

    def test_multiple_api_provider_cloud_formation(self):
        resources = OrderedDict()
        resources["TestApi"] = {
            "Type": "AWS::ApiGateway::RestApi",
            "Properties": {
                "StageName": "dev",
                "Body": {
                    "paths": {
                        "/path": {
                            "get": {
                                "x-amazon-apigateway-integration": {
                                    "httpMethod": "POST",
                                    "type": "aws_proxy",
                                    "uri": {
                                        "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31"
                                                   "/functions/${NoApiEventFunction.Arn}/invocations",
                                    },
                                    "responses": {},
                                },
                            }
                        }

                    }
                }
            }
        }
        resources["OtherApi"] = {
            "Type": "AWS::Serverless::Api",
            "Properties": {
                "StageName": "dev",
                "DefinitionBody": {
                    "paths": {
                        "/path": {
                            "get": {
                                "x-amazon-apigateway-integration": {
                                    "httpMethod": "POST",
                                    "type": "aws_proxy",
                                    "uri": {
                                        "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31"
                                                   "/functions/${NoApiEventFunction.Arn}/invocations",
                                    },
                                    "responses": {},
                                },
                            }
                        }

                    }
                }
            }
        }

        provider = ApiProvider.find_api_provider(resources)
        self.assertTrue(isinstance(provider, CfnApiProvider))
