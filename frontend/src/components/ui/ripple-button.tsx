import React, { MouseEvent, useEffect, useRef, useState } from "react"

import { cn } from "../../lib/utils"

interface RippleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  rippleColor?: string
  duration?: string
}

export const RippleButton = React.forwardRef<
  HTMLButtonElement,
  RippleButtonProps
>(
  (
    {
      className,
      children,
      rippleColor = "#ffffff",
      duration = "600ms",
      onClick,
      ...props
    },
    ref
  ) => {
    const [buttonRipples, setButtonRipples] = useState<
      Array<{ x: number; y: number; size: number; key: number }>
    >([])
    const nextRippleKey = useRef(0)
    const cleanupTimers = useRef<Array<ReturnType<typeof setTimeout>>>([])

    const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
      createRipple(event)
      onClick?.(event)
    }

    const createRipple = (event: MouseEvent<HTMLButtonElement>) => {
      const button = event.currentTarget
      const rect = button.getBoundingClientRect()
      const size = Math.max(rect.width, rect.height)
      const x = event.clientX - rect.left - size / 2
      const y = event.clientY - rect.top - size / 2

      const key = nextRippleKey.current++
      const newRipple = { x, y, size, key }
      setButtonRipples((prevRipples) => [...prevRipples, newRipple])

      const durationValue = Number.parseFloat(duration)
      const durationMs = Number.isFinite(durationValue)
        ? duration.endsWith("ms")
          ? durationValue
          : duration.endsWith("s")
            ? durationValue * 1000
            : durationValue
        : 600
      const timer = setTimeout(() => {
        setButtonRipples((prevRipples) =>
          prevRipples.filter((ripple) => ripple.key !== key)
        )
        cleanupTimers.current = cleanupTimers.current.filter(
          (candidate) => candidate !== timer
        )
      }, durationMs)
      cleanupTimers.current.push(timer)
    }

    useEffect(() => {
      return () => {
        cleanupTimers.current.forEach(clearTimeout)
        cleanupTimers.current = []
      }
    }, [])

    return (
      <button
        className={cn(
          "bg-background text-primary relative flex cursor-pointer items-center justify-center overflow-hidden rounded-lg border-2 px-4 py-2 text-center",
          className
        )}
        onClick={handleClick}
        ref={ref}
        {...props}
      >
        <div className="relative z-10">{children}</div>
        <span className="pointer-events-none absolute inset-0">
          {buttonRipples.map((ripple) => (
            <span
              className="animate-rippling bg-background absolute rounded-full opacity-30"
              key={ripple.key}
              style={
                {
                  width: `${ripple.size}px`,
                  height: `${ripple.size}px`,
                  top: `${ripple.y}px`,
                  left: `${ripple.x}px`,
                  backgroundColor: rippleColor,
                  transform: `scale(0)`,
                  "--duration": duration,
                } as React.CSSProperties
              }
            />
          ))}
        </span>
      </button>
    )
  }
)

RippleButton.displayName = "RippleButton"
