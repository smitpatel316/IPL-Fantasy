/** localStorage key for the manual theme override. Shared between the
 *  server-rendered init script (layout) and the client ThemeProvider —
 *  kept in a module with no "use client" so both can import it. */
export const THEME_STORAGE_KEY = "ipl-theme";
