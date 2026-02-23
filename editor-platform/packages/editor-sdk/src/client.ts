export type EditorSDKConfig = {
  graphqlUrl: string;
  apiKey: string;
};

export async function gql<T>(
  cfg: EditorSDKConfig,
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
