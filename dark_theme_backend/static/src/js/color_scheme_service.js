/** @odoo-module **/

import { whenReady } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

import { switchColorSchemeItem } from "./color_scheme_menu_items";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");

export class ColorSchemeService {
    constructor(env, { cookie, ui }) {
        this.cookie = cookie;
        this.ui = ui;
        whenReady(() => this.applyColorScheme());
    }
    /**
     * @returns {String} The color scheme configured by the end-user
     */
    get activeColorScheme() {
        const cookies = this.cookie.current;
        return cookies.configured_color_scheme || cookies.color_scheme || "light";
    }
    /**
     * @returns {String} the color scheme that should be loaded from the server
     */
    get effectiveColorScheme() {
        return this.activeColorScheme;
    }
    /**
     * @param {String} scheme
     */
    switchToColorScheme(scheme) {
        this.cookie.setCookie("configured_color_scheme", scheme);
        this.applyColorScheme();
    }
    /**
     * Check if the currently loaded assets correspond to the current effective
     * color scheme. If not, reload the page to get the correct assets.
     */
    applyColorScheme() {
        const effectiveScheme = this.effectiveColorScheme;
        if (effectiveScheme !== (this.cookie.current.color_scheme || "light")) {
            this.cookie.setCookie("color_scheme", effectiveScheme);
            this.ui.block();
            browser.location.reload();
        }
    }
}

export const colorSchemeService = {
    dependencies: ["cookie", "ui"],

    start(env, services) {
        userMenuRegistry.add("color_scheme.switch", switchColorSchemeItem);
        return new ColorSchemeService(env, services);
    },
};
serviceRegistry.add("color_scheme", colorSchemeService);
