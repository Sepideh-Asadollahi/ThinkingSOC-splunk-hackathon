"use client"

import { Trash2Icon } from "lucide-react"

import {
  Dialog,
  NeonDialogContent,
  NeonDialogFooter,
  NeonDialogFooterButton,
  NeonDialogHeaderWithIcon,
} from "@/components/neon-glass"

type SocChatDeleteDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  onConfirm: () => void
  deleting?: boolean
}

export function SocChatDeleteDialog({
  open,
  onOpenChange,
  title,
  onConfirm,
  deleting = false,
}: SocChatDeleteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <NeonDialogContent className="max-w-md" accent="teal" variant="danger">
        <NeonDialogHeaderWithIcon
          icon={<Trash2Icon className="size-5" />}
          title="Delete chat?"
          description={`This permanently removes "${title}" and all messages. This cannot be undone.`}
        />
        <NeonDialogFooter>
          <NeonDialogFooterButton
            footerVariant="secondary"
            onClick={() => onOpenChange(false)}
            disabled={deleting}
          >
            Cancel
          </NeonDialogFooterButton>
          <NeonDialogFooterButton
            className="border-red-500/40 bg-red-950/50 text-red-100 hover:bg-red-900/60"
            onClick={onConfirm}
            disabled={deleting}
          >
            {deleting ? "Deleting…" : "Delete"}
          </NeonDialogFooterButton>
        </NeonDialogFooter>
      </NeonDialogContent>
    </Dialog>
  )
}
