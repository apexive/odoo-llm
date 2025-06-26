/** @odoo-module **/

export function switchColorSchemeItem(env) {
    return {
        type: "switch",
        id: "color_scheme.switch_theme",
        description: env._t("Dark Mode"),
        callback: () => {
            const cookie = env.services.cookie.current.color_scheme;
            const scheme = cookie === "dark" ? "light" : "dark";
            env.services.color_scheme.switchToColorScheme(scheme);
        },
        isChecked: env.services.cookie.current.color_scheme === "dark",
        sequence: 30,
    };
}
