import Head from 'next/head'

export default function Docs(){
  return (
    <>
      <Head>
        <title>API Docs - LangChain Web</title>
        <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
      </Head>
      <div style={{padding: '20px'}}>
        <h1 className="text-2xl font-bold mb-4">API Documentation</h1>
        <div id="redoc-container">
          <redoc spec-url="/openapi.yaml"></redoc>
        </div>
      </div>
    </>
  )
}
