import { Component } from "@tcrm/owl";

export class MessageNotificationPopover extends Component {
    static template = "mail.MessageNotificationPopover";
    static props = ["message", "close?"];
}
