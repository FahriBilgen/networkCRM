import "./style.css";
import { UIController } from "./ui/UIController";
const mountNode = document.querySelector("#app");
if (!mountNode) {
    throw new Error("Missing #app mount node");
}
const controller = new UIController(mountNode);
controller.bootstrap().catch((error) => {
    console.error("Failed to bootstrap UI", error);
    const notice = document.createElement("pre");
    notice.textContent = String(error);
    mountNode.appendChild(notice);
});
