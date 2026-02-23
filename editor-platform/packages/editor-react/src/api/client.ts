export type EditorClientConfig = {
  graphqlUrl: string;      // e.g. http://localhost:8000/graphql
  apiKey: string;          // x-api-key
};

export async function gql<T>(
  cfg: EditorClientConfig,
  query: string,
  variables?: Record<string, any>
): Promise<T> {
  const res = await fetch(cfg.graphqlUrl, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": cfg.apiKey,
    },
    body: JSON.stringify({ query, variables }),
  });

  const json = await res.json();
  if (json.errors?.length) throw new Error(json.errors[0].message);
  return json.data as T;
}
