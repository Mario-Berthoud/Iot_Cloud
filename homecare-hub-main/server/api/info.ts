export default defineEventHandler(async (event) => {
  const remote = process.env.VIZ_REMOTE || "http://viz.sif.svc.cluster.local:8080";
  let data = null
  try {
    if (event.method == "DELETE") {
      const data = await readBody(event);
      return $fetch(`${remote}/api/info`, {
        method: event.method,
        body: data
      })
    }
    return $fetch(`${remote}/api/info`)
  } catch (err) {
    console.log(`Failed to carry request for ${remote}`)
    console.log(`The error is ${err}`)
  }
})
