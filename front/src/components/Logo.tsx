import logo from "../alfalogo.svg";

export function Logo({ className }: { className?: string }) {
  return <img src={logo} alt="" className={className} />;
}
