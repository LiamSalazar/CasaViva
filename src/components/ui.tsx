"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Heart,
  Menu,
  Search,
  Share2,
  X,
  Check,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { copyText } from "@/lib/utils";
import { useCasaViva } from "@/services";
import { trackEvent } from "@/components/analytics-provider";

export function CasaVivaLogo({
  variant = "dark",
  compact = false,
}: {
  variant?: "light" | "dark";
  compact?: boolean;
}) {
  return (
    <span
      className={`cv-logo ${variant} ${compact ? "compact" : ""}`}
      aria-label="CasaViva"
    >
      <span>{compact ? "CV" : "CASAVIVA"}</span>
    </span>
  );
}

type ToastContextType = { toast: (message: string) => void };
const ToastContext = createContext<ToastContextType>({
  toast: () => undefined,
});
export const useToast = () => useContext(ToastContext);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<{ id: number; text: string }[]>([]);
  const toast = useCallback((text: string) => {
    const id = Date.now();
    setMessages((m) => [...m, { id, text }]);
    window.setTimeout(
      () => setMessages((m) => m.filter((x) => x.id !== id)),
      2800,
    );
  }, []);
  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="toast-stack" aria-live="polite">
        <AnimatePresence>
          {messages.map((m) => (
            <motion.div
              className="toast"
              key={m.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              transition={{ duration: 0.2 }}
            >
              <Check size={16} />
              {m.text}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  useEffect(() => {
    const d = ref.current;
    const close = () => onClose();
    d?.addEventListener("close", close);
    return () => d?.removeEventListener("close", close);
  }, [onClose]);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "modal-wide" : ""}`}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="modal-panel">
        {title && (
          <div className="modal-head">
            <h2>{title}</h2>
            <button
              className="icon-button"
              onClick={onClose}
              aria-label="Cerrar"
            >
              <X />
            </button>
          </div>
        )}
        {children}
      </div>
    </dialog>
  );
}

export function ConfirmDialog({
  open,
  title,
  description,
  onClose,
  onConfirm,
  confirmLabel = "Eliminar",
}: {
  open: boolean;
  title: string;
  description: string;
  onClose: () => void;
  onConfirm: () => void;
  confirmLabel?: string;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="muted">{description}</p>
      <div className="modal-actions">
        <button className="button secondary" onClick={onClose}>
          Cancelar
        </button>
        <button
          className="button danger"
          onClick={() => {
            onConfirm();
            onClose();
          }}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}

export function Drawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className={`drawer-wrap ${open ? "open" : ""}`} aria-hidden={!open}>
      <button
        className="drawer-scrim"
        onClick={onClose}
        aria-label="Cerrar filtros"
      />
      <aside className="drawer">
        <div className="drawer-head">
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Cerrar">
            <X />
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}

const nav = [
  ["Propiedades", "/propiedades"],
  ["Desarrollos", "/desarrollos"],
  ["Guías", "/guias"],
  ["Nosotros", "/nosotros"],
];
export function PublicHeader({
  overlay = false,
  search = false,
}: {
  overlay?: boolean;
  search?: boolean;
}) {
  const [menu, setMenu] = useState(false);
  const router = useRouter();
  const [query, setQuery] = useState("");
  return (
    <header
      className={`public-header ${overlay ? "overlay" : ""} ${search ? "search-header" : ""}`}
    >
      <Link href="/" aria-label="Ir al inicio">
        <CasaVivaLogo variant={overlay || search ? "light" : "dark"} />
      </Link>
      {search && (
        <form
          className="header-search"
          onSubmit={(e) => {
            e.preventDefault();
            router.push(`/propiedades?query=${encodeURIComponent(query)}`);
          }}
        >
          <Search size={18} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar localidad"
            aria-label="Buscar localidad"
          />
        </form>
      )}
      <nav className="desktop-nav">
        {nav.map(([label, href]) => (
          <Link href={href} key={href}>
            {label}
          </Link>
        ))}
        <Link href="/favoritos" aria-label="Favoritos">
          <Heart size={20} />
        </Link>
      </nav>
      <button
        className="mobile-menu-button"
        onClick={() => setMenu(true)}
        aria-label="Abrir menú"
      >
        <Menu />
      </button>
      <Drawer
        open={menu}
        onClose={() => setMenu(false)}
        title="Explora CasaViva"
      >
        <nav className="mobile-nav">
          {nav.map(([label, href]) => (
            <Link href={href} key={href} onClick={() => setMenu(false)}>
              {label}
              <ChevronRight />
            </Link>
          ))}
          <Link href="/favoritos" onClick={() => setMenu(false)}>
            Favoritos
            <Heart />
          </Link>
          <Link href="/encontrar" onClick={() => setMenu(false)}>
            Encontrar mi hogar
            <Search />
          </Link>
        </nav>
      </Drawer>
    </header>
  );
}

export const PublicHeaderOverlay = () => <PublicHeader overlay />;
export const SearchHeader = () => <PublicHeader search />;
export function Footer() {
  const { siteSettings } = useCasaViva();
  const socialLinks = [
    ["Instagram", siteSettings?.instagram_url, "Instagram de CasaViva"],
    ["Facebook", siteSettings?.facebook_url, "Facebook de CasaViva"],
    ["TikTok", siteSettings?.tiktok_url, "TikTok de CasaViva"],
  ].filter((item): item is [string, string, string] => Boolean(item[1]));
  return (
    <footer className="site-footer">
      <div className="footer-grid">
        <div>
          <CasaVivaLogo />
          <p>Una forma más clara de encontrar hogar.</p>
        </div>
        <FooterCol
          title="Explora"
          items={[
            ["Propiedades", "/propiedades"],
            ["Desarrollos", "/desarrollos"],
            ["Ubicaciones", "/ubicaciones/tecamac"],
          ]}
        />
        <FooterCol
          title="CasaViva"
          items={[
            ["Nosotros", "/nosotros"],
            ["Guías", "/guias"],
            ["Contacto", "/contacto"],
          ]}
        />
        <FooterCol
          title="Legal"
          items={[
            ["Aviso de privacidad", "/aviso-de-privacidad"],
            ["Términos", "/terminos"],
          ]}
        />
        <div>
          <h3>Síguenos</h3>
          {siteSettings?.contact_email && <a href={`mailto:${siteSettings.contact_email}`}>{siteSettings.contact_email}</a>}
          {socialLinks.map(([label, href, ariaLabel]) => <a key={label} href={href} target="_blank" rel="noopener noreferrer" aria-label={ariaLabel}>{label}</a>)}
        </div>
      </div>
      <div className="footer-bottom">
        <span>© 2026 CasaViva</span>
        <span>Hecho para encontrar hogar en México</span>
      </div>
    </footer>
  );
}
function FooterCol({ title, items }: { title: string; items: string[][] }) {
  return (
    <div>
      <h3>{title}</h3>
      {items.map(([l, h]) => (
        <Link key={h} href={h}>
          {l}
        </Link>
      ))}
    </div>
  );
}

export function FavoriteButton({
  id,
  label = false,
}: {
  id: string;
  label?: boolean;
}) {
  const { favorites, toggleFavorite } = useCasaViva();
  const active = favorites.includes(id);
  const { toast } = useToast();
  return (
    <button
      className={`icon-button favorite ${active ? "active" : ""}`}
      aria-label={active ? "Quitar de favoritos" : "Guardar en favoritos"}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void trackEvent(active ? "favorite_removed" : "favorite_added", {}, { listing: id }).catch(() => undefined);
        toggleFavorite(id);
        toast(active ? "Eliminado de favoritos" : "Añadido a favoritos");
      }}
    >
      <Heart fill={active ? "currentColor" : "none"} />
      {label && <span>{active ? "Guardada" : "Guardar"}</span>}
    </button>
  );
}
export function ShareButton({ label = false }: { label?: boolean }) {
  const { toast } = useToast();
  const share = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const data = { title: document.title, url: location.href };
    if (navigator.share) await navigator.share(data);
    else {
      await copyText(location.href);
      toast("Enlace copiado");
    }
  };
  return (
    <button className="icon-button" onClick={share} aria-label="Compartir">
      <Share2 />
      {label && <span>Compartir</span>}
    </button>
  );
}
export function EmptyState({
  title,
  body,
  href,
  action,
}: {
  title: string;
  body: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="empty-state">
      <h2>{title}</h2>
      <p>{body}</p>
      {href && (
        <Link className="button" href={href}>
          {action || "Explorar"}
        </Link>
      )}
    </div>
  );
}
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-label="Cargando" />;
}
export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "danger";
}) {
  return <span className={`status-badge ${tone}`}>{children}</span>;
}
export function ExternalLinkButton({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className="text-link">
      {children}
      <ExternalLink size={14} />
    </Link>
  );
}
