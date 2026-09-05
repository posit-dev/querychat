import { installHandoff } from "./handoff-core";

const Shiny = (window as any).Shiny;
if (Shiny) installHandoff(Shiny);
