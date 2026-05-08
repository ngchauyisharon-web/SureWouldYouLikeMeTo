import Phaser from "phaser";
import { theme } from "../theme";

function hex(color: string): number {
  return Phaser.Display.Color.HexStringToColor(color).color;
}

export class PlayScene extends Phaser.Scene {
  constructor() {
    super("Play");
  }

  create() {
    const w = this.scale.width;
    const h = this.scale.height;

    this.cameras.main.setBackgroundColor(hex(theme.surface));

    const cloud = (cx: number, cy: number, sc: number) => {
      const c = this.add.graphics();
      c.fillStyle(0xffffff, 0.55);
      c.fillCircle(0, 0, 40 * sc);
      c.fillCircle(35 * sc, -5 * sc, 48 * sc);
      c.fillCircle(70 * sc, 0, 42 * sc);
      c.setPosition(cx, cy);
    };
    cloud(w * 0.15, h * 0.22, 0.9);
    cloud(w * 0.55, h * 0.12, 0.65);
    cloud(w * 0.82, h * 0.2, 0.75);

    const hill = this.add.graphics();
    hill.fillStyle(hex(theme.tertiary), 0.35);
    hill.beginPath();
    hill.moveTo(0, h);
    hill.lineTo(0, h * 0.62);
    hill.lineTo(w * 0.35, h * 0.52);
    hill.lineTo(w * 0.72, h * 0.58);
    hill.lineTo(w, h * 0.48);
    hill.lineTo(w, h);
    hill.closePath();
    hill.fillPath();

    const labelStyle = {
      fontFamily: theme.fontFamily,
      fontSize: "42px",
      fontStyle: "900" as const,
    };

    const robot = this.add
      .text(w * 0.28, h * 0.68, "AI", {
        ...labelStyle,
        color: theme.secondary,
      })
      .setOrigin(0.5, 1);

    const player = this.add
      .text(w * 0.72, h * 0.68, "YOU", {
        ...labelStyle,
        color: theme.primary,
      })
      .setOrigin(0.5, 1);

    if (this.textures.exists("robot")) {
      this.add.image(w * 0.28, h * 0.72, "robot").setScale(0.35).setOrigin(0.5, 1);
      robot.destroy();
    }
    if (this.textures.exists("player")) {
      this.add.image(w * 0.72, h * 0.72, "player").setScale(0.35).setOrigin(0.5, 1);
      player.destroy();
    }

    this.add
      .text(w / 2, h * 0.06, "SURE! WOULD YOU LIKE ME TO…?", {
        fontFamily: theme.fontFamily,
        fontSize: `${Math.min(18, w / 42)}px`,
        fontStyle: "900",
        color: theme.secondary,
      })
      .setOrigin(0.5, 0);
  }
}
