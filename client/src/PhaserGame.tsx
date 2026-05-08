import { useEffect, useRef } from "react";
import Phaser from "phaser";
import { BootScene } from "./phaser/BootScene";
import { PlayScene } from "./phaser/PlayScene";
import { theme } from "./theme";

type Props = {
  height?: number;
};

export function PhaserGame({ height = 320 }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<Phaser.Game | null>(null);

  useEffect(() => {
    const el = hostRef.current;
    if (!el) return;

    const config: Phaser.Types.Core.GameConfig = {
      type: Phaser.AUTO,
      parent: el,
      width: el.clientWidth || 640,
      height,
      transparent: false,
      scene: [BootScene, PlayScene],
      scale: {
        mode: Phaser.Scale.RESIZE,
        autoCenter: Phaser.Scale.CENTER_BOTH,
      },
      backgroundColor: theme.surface,
    };

    const game = new Phaser.Game(config);
    gameRef.current = game;

    return () => {
      game.destroy(true);
      gameRef.current = null;
    };
  }, [height]);

  return (
    <div
      ref={hostRef}
      style={{
        width: "100%",
        height,
        borderRadius: 16,
        overflow: "hidden",
        border: `2px solid color-mix(in srgb, ${theme.outline} 55%, transparent)`,
        boxShadow: `0 18px 40px color-mix(in srgb, ${theme.onSurface} 18%, transparent)`,
      }}
    />
  );
}
