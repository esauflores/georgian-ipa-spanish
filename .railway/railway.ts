import { defineRailway, github, project, service } from "railway/iac";

export const partial = "georgian-dictionary";

export default defineRailway(() => {
  const editions = [
    { name: "georgian-dictionary", branch: "main" },
    { name: "heavy-georgian-dictionary", branch: "heavy-insults" },
  ];

  return project("demos", {
    variables: { managed: false },
    resources: editions.map(({ name, branch }) => service(name, {
      source: github("esauflores/georgian-ipa-spanish", {
        branch,
        checkSuites: false,
      }),
      build: { buildEnvironment: "V3" },
      healthcheck: "/",
      healthcheckTimeout: 60,
      replicas: { "us-west2": 1 },
      deploy: {
        limitOverride: { containers: { cpu: 0.5, memoryBytes: 500000000 } },
        sleepApplication: true,
      },
      domains: [`${name}.esauflores.com`],
    })),
  });
});
