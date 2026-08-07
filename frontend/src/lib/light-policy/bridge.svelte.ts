import type { HassLike } from "./types";

export const bridge = $state<{ hass: HassLike | null }>({ hass: null });
