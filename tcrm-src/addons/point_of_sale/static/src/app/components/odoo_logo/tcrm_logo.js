import { Component } from "@tcrm/owl";

export class tcrmLogo extends Component {
    static template = "point_of_sale.tcrmLogo";
    static props = {
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        monochrome: { type: Boolean, optional: true },
    };
    static defaultProps = {
        class: "",
        style: "",
        monochrome: false,
    };
}
