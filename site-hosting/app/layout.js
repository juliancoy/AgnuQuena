export const metadata = {
  title: "AgnuQuena Acoustic Lab",
  description: "Interactive WebGPU exterior-flow LES of the generated quena geometry and turbulent mouth jet.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>{children}</body>
    </html>
  );
}
