type LogoProps = {
  size?: number;
  className?: string;
};

export function Logo({ size = 24, className }: LogoProps) {
  return (
    <img
      src="/logo-mark.png"
      alt="NOBS AI"
      width={size}
      height={size}
      className={className}
    />
  );
}
