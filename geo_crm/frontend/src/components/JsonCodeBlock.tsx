import { Highlight, themes } from "prism-react-renderer";

/**
 * Bloc de code JSON / JSON-LD avec coloration Prism.
 * `javascript` : même tokenizer que le JSON côté prévisualisation, sans enregistrement
 * de grammaire supplémentaire (bundle stable sous Vite).
 */
export function JsonCodeBlock({ code }: { code: string }) {
  return (
    <Highlight
      theme={themes.oneDark}
      code={code}
      language="javascript"
    >
      {({ className, style, tokens, getLineProps, getTokenProps }) => (
        <pre
          className={`${className} m-0 p-0 bg-transparent text-[11px] leading-relaxed font-mono overflow-x-auto`}
          style={style}
        >
          {tokens.map((line, i) => (
            <div key={i} {...getLineProps({ line })}>
              {line.map((token, key) => (
                <span key={key} {...getTokenProps({ token })} />
              ))}
            </div>
          ))}
        </pre>
      )}
    </Highlight>
  );
}
