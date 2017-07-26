package main

import (
	"fmt"
	"log"
	"os"

	"io/ioutil"

	"io"
	"sync"

	"encoding/json"

	"github.com/awslabs/goformation"
	"github.com/awslabs/goformation/resources"
	"github.com/codegangsta/cli"
)

func invoke(c *cli.Context) {

	// Setup the logger
	stdout := io.Writer(os.Stdout)
	stderr := io.Writer(os.Stderr)
	logarg := c.String("log")

	if len(logarg) > 0 {
		if logFile, err := os.Create(logarg); err == nil {
			stderr = io.Writer(logFile)
			stdout = io.Writer(logFile)
			log.SetOutput(stderr)
		} else {
			log.Fatalf("Failed to open log file %s: %s\n", c.String("log"), err)
		}
	}

	name := c.Args().First()
	if name == "" {
		fmt.Fprintf(os.Stderr, "ERROR: You must provide a function identifier (function's Logical ID in the SAM template) as the first argument.\n")
		os.Exit(1)
	}

	template, _, errs := goformation.Open(c.String("template"))
	if len(errs) > 0 {
		for _, err := range errs {
			log.Printf("%s\n", err)
		}
		os.Exit(1)
	}

	log.Printf("Successfully parsed %s (version %s)\n", c.String("template"), template.Version())

	// Find the specified function in the SAM template
	var function resources.AWSServerlessFunction
	functions := template.GetResourcesByType("AWS::Serverless::Function")
	for resourceName, resource := range functions {
		if resourceName == name {
			if f, ok := resource.(resources.AWSServerlessFunction); ok {
				function = f
			}
		}
	}

	if function == nil {
		log.Fatalf("Could not find a AWS::Serverless::Function with logical ID '%s'\n", name)
	}

	// Check connectivity to docker
	dockerVersion, err := getDockerVersion()
	if err != nil {
		log.Printf("Running AWS SAM projects locally requires Docker. Have you got it installed?\n")
		log.Printf("%s\n", err)
		os.Exit(1)
	}

	log.Printf("Connected to Docker %s", dockerVersion)

	// FIXME: Move all the argument parsing into a shared file - invoke and start commands have duplicate code
	envVarsFile := c.String("env-vars")
	envVarsOverrides := map[string]map[string]string{}
	if len(envVarsFile) > 0 {

		f, err := os.Open(c.String("env-vars"))
		if err != nil {
			log.Fatalf("Failed to open environment variables values file\n%s\n", err)
		}

		data, err := ioutil.ReadAll(f)
		if err != nil {
			log.Fatalf("Unable to read the environment variable values file\n%s\n", err)
		}

		// This is a JSON of structure {FunctionName: {key:value}, FunctionName: {key:value}}
		if err = json.Unmarshal(data, &envVarsOverrides); err != nil {
			log.Fatalf("Environment variable values must be a valid JSON\n%s\n", err)
		}

	}

	// Find the env-vars map for the function
	funcEnvVarsOverrides := envVarsOverrides[name]
	if funcEnvVarsOverrides == nil {
		funcEnvVarsOverrides = map[string]string{}
	}

	runt, err := NewRuntime(function, funcEnvVarsOverrides)
	if err != nil {
		log.Fatalf("Could not initiate %s runtime: %s\n", function.Runtime(), err)
	}

	eventFile := c.String("event")
	event := ""
	if eventFile == "" {
		// The event payload wasn't provided with --event, so read from stdin
		log.Printf("Reading invoke payload from stdin (you can also pass it from file with --event)\n")
		pb, err := ioutil.ReadAll(os.Stdin)
		if err != nil {
			log.Fatalf("Could not read event from stdin: %s\n", err)
		}
		event = string(pb)
	} else {
		// The event payload should be read from the file provided
		pb, err := ioutil.ReadFile(eventFile)
		if err != nil {
			log.Fatalf("Could not read event from file: %s\n", err)
		}
		event = string(pb)
	}

	stdoutTxt, stderrTxt, err := runt.Invoke(event)
	if err != nil {
		log.Fatalf("Could not invoke function: %s\n", err)
	}

	var wg sync.WaitGroup
	wg.Add(2)

	go func() {
		io.Copy(stderr, stderrTxt)
		wg.Done()
	}()

	go func() {
		io.Copy(stdout, stdoutTxt)
		wg.Done()
	}()

	wg.Wait()

}
