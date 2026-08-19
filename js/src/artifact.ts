import { installArtifact } from "./artifact-core";

const Shiny = (window as any).Shiny;
if (Shiny) installArtifact(Shiny);
