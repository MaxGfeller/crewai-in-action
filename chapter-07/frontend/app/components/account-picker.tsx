"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { autoUpdate, flip, offset, shift, size, useFloating } from "@floating-ui/react-dom";
import { ShieldCheck } from "lucide-react";

import type { AccountSummary } from "./types";

export function AccountPicker({
  accounts,
  selectedAccount,
  open,
  disabled,
  onOpenChange,
  onSelect,
}: {
  accounts: AccountSummary[];
  selectedAccount?: AccountSummary;
  open: boolean;
  disabled: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (account: AccountSummary) => void;
}) {
  const { refs, floatingStyles, update } = useFloating<HTMLButtonElement>({
    open,
    placement: "bottom-start",
    strategy: "fixed",
    whileElementsMounted: autoUpdate,
    middleware: [
      offset(8),
      flip({ padding: 12 }),
      shift({ padding: 12 }),
      size({
        padding: 12,
        apply({ availableWidth, availableHeight, elements, rects }) {
          const width = Math.min(
            420,
            Math.max(rects.reference.width, availableWidth),
          );
          Object.assign(elements.floating.style, {
            minWidth: `${rects.reference.width}px`,
            width: `${width}px`,
            maxWidth: `${Math.max(rects.reference.width, availableWidth)}px`,
            maxHeight: `${Math.max(180, availableHeight)}px`,
          });
        },
      }),
    ],
  });

  useEffect(() => {
    if (!open) {
      return;
    }

    function closeOnOutsidePointer(event: PointerEvent) {
      const target = event.target as Node;
      if (
        refs.reference.current?.contains(target)
        || refs.floating.current?.contains(target)
      ) {
        return;
      }
      onOpenChange(false);
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    }

    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [onOpenChange, open, refs.floating, refs.reference]);

  useEffect(() => {
    if (open) {
      void update();
    }
  }, [accounts.length, open, selectedAccount?.account_id, update]);

  return (
    <div className="accountMenu">
      <button
        ref={refs.setReference}
        className="accountMenuButton"
        onClick={() => onOpenChange(!open)}
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <ShieldCheck size={18} />
        <span>{selectedAccount?.name ?? "Accounts"}</span>
        <small>{selectedAccount?.health ?? `${accounts.length} tracked`}</small>
      </button>

      {open && typeof document !== "undefined" ? createPortal(
        <div
          ref={refs.setFloating}
          className="accountPopover"
          role="menu"
          style={floatingStyles}
        >
          {accounts.length === 0 ? (
            <p className="empty">No accounts loaded.</p>
          ) : (
            accounts.map((account) => (
              <button
                className="accountOption"
                key={account.account_id}
                onClick={() => onSelect(account)}
                role="menuitem"
              >
                <span className="accountOptionName">
                  <strong>{account.name}</strong>
                  <small>{account.owner}</small>
                </span>
                <span className="accountOptionDetails">
                  <span className={`health health-${account.health}`}>{account.health}</span>
                  <span className="accountMeta">${account.arr_usd.toLocaleString()}</span>
                  <span className="accountMeta">{account.renewal_date}</span>
                </span>
              </button>
            ))
          )}
        </div>,
        document.body,
      ) : null}
    </div>
  );
}
